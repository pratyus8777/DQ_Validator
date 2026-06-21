from flask import Flask, jsonify, request, send_file
import pandas as pd
import os
import io
import json
import logging

from agents.remediation_agent import RemediationAgent
from semantic_engine.interpreter import OllamaClient, SemanticRuleInterpreter

logger = logging.getLogger(__name__)


def _read_csv_if_exists(path):
    """Read CSV file if exists, otherwise return None"""
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            return None
    return None


def create_app(data_dir: str = "data", output_dir: str = "output"):
    """Factory function to create Flask app with routes and logic"""
    app = Flask(__name__)

    custom_kpi_path = os.path.join(data_dir, "custom_kpis.json")

    def load_custom_kpis():
        """Load custom KPIs from JSON file"""
        if os.path.exists(custom_kpi_path):
            try:
                with open(custom_kpi_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_custom_kpis(kpis):
        """Save custom KPIs to JSON file"""
        os.makedirs(os.path.dirname(custom_kpi_path) or ".", exist_ok=True)
        with open(custom_kpi_path, 'w') as f:
            json.dump(kpis, f, indent=2)

    # ===== Routes =====

    @app.route('/rules', methods=['GET'])
    def get_rules():
        """Get cleansing rules as JSON"""
        try:
            from data_io.db_helpers import read_guidewire_cleansing_rules
            df = read_guidewire_cleansing_rules()
        except Exception:
            path = os.path.join(data_dir, 'Guidewire_Policy_DataCleansing_Rules.csv')
            if not os.path.exists(path):
                return jsonify({'error': 'rules file not found'}), 404
            df = pd.read_csv(path)
        return df.to_json(orient='records')

    @app.route('/data', methods=['GET'])
    def get_data():
        """Get data preview (cleaned if available, else original)"""
        out_path = os.path.join(output_dir, 'Sample_Policy_Data_clean.csv')
        if os.path.exists(out_path):
            df = pd.read_csv(out_path)
            return df.to_json(orient='records')

        try:
            from data_io.db_helpers import read_sample_policy_data
            df = read_sample_policy_data(limit=100)
            return df.to_json(orient='records')
        except Exception:
            data_path = os.path.join(data_dir, 'Sample_Policy_Data.csv')
            if not os.path.exists(data_path):
                return jsonify({'error': 'no data file found'}), 404
            df = pd.read_csv(data_path)
            return df.to_json(orient='records')

    @app.route('/apply', methods=['POST'])
    def apply_rules():
        """Apply cleansing rules and return preview + per-column change counts"""
        content_type = request.headers.get('Content-Type', '')

        data_path = os.path.join(data_dir, 'Sample_Policy_Data.csv')
        if not os.path.exists(data_path):
            return jsonify({'error': 'input data not found'}), 404
        df = pd.read_csv(data_path)

        # Parse incoming rules (JSON or CSV format)
        cleansing_df = None
        try:
            if 'application/json' in content_type:
                payload = request.get_json()
                cleansing_df = pd.DataFrame(payload)
            else:
                text = request.get_data(as_text=True)
                cleansing_df = pd.read_csv(io.StringIO(text))
        except Exception as e:
            logger.exception('Failed to parse incoming rules')
            return jsonify({'error': f'failed to parse rules: {e}'}), 400

        # Run remediation agent
        ollama = OllamaClient('http://localhost:11434')
        rem_agent = RemediationAgent(ollama)
        context = {'data': df, 'cleansing_rules': cleansing_df, 'remediation_allowed': True}

        try:
            result = rem_agent.run(context)
            cleaned = result.get('data')
        except Exception as e:
            logger.exception('Remediation failed')
            return jsonify({'error': str(e)}), 500

        # Save cleaned data
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, 'Sample_Policy_Data_clean.csv')
        cleaned.to_csv(out_path, index=False)

        # Calculate per-column changes
        preview = cleaned.head(10).to_dict(orient='records')
        changes = {}
        for col in df.columns:
            b = df[col].fillna('__NA__').astype(str)
            a = cleaned[col].fillna('__NA__').astype(str) if col in cleaned.columns else pd.Series(['__NA__']*len(df))
            changes[col] = int((~b.eq(a)).sum())

        return jsonify({
            'status': 'success',
            'rows': len(cleaned),
            'preview': preview,
            'changes': changes,
            'download': '/download'
        })

    @app.route('/download', methods=['GET'])
    def download():
        """Download cleaned CSV file"""
        out_path = os.path.join(output_dir, 'Sample_Policy_Data_clean.csv')
        if not os.path.exists(out_path):
            return jsonify({'error': 'output not found'}), 404
        return send_file(out_path, as_attachment=True)

    @app.route('/validate_llm', methods=['GET'])
    def validate_llm():
        """Validate LLM availability and test rule interpretation"""
        try:
            from data_io.db_helpers import read_guidewire_cleansing_rules
            cleansing_df = read_guidewire_cleansing_rules()
        except Exception:
            path = os.path.join(data_dir, 'Guidewire_Policy_DataCleansing_Rules.csv')
            if not os.path.exists(path):
                return jsonify({'error': 'rules file not found'}), 404
            cleansing_df = pd.read_csv(path)

        ollama = OllamaClient('http://localhost:11434')
        interpreter = SemanticRuleInterpreter(ollama)

        try:
            interpreted = interpreter.interpret_rule_csv(cleansing_df)
            sample = interpreted[:5]
            return jsonify({
                'llm_available': ollama.available,
                'interpreted_count': len(interpreted),
                'sample': sample
            })
        except Exception as e:
            logger.exception('LLM interpretation failed')
            return jsonify({'error': str(e)}), 500

    @app.route('/kpis', methods=['GET', 'POST'])
    def kpis():
        """Get base + custom KPIs, or add/update custom KPIs"""
        base_path = os.path.join(data_dir, 'DQ_Dashboard_KPIs.csv')
        base = _read_csv_if_exists(base_path)
        base_list = base.to_dict(orient='records') if base is not None else []

        if request.method == 'GET':
            custom = load_custom_kpis()
            return jsonify({'base_kpis': base_list, 'custom_kpis': custom})

        # POST: add custom KPI
        try:
            payload = request.get_json()
            if isinstance(payload, list):
                save_custom_kpis(payload)
                return jsonify({'status': 'ok', 'saved': len(payload)})
            elif isinstance(payload, dict):
                custom = load_custom_kpis()
                custom.append(payload)
                save_custom_kpis(custom)
                return jsonify({'status': 'ok', 'added': payload})
            else:
                return jsonify({'error': 'invalid payload'}), 400
        except Exception as e:
            logger.exception('Failed to save kpis')
            return jsonify({'error': str(e)}), 500

    @app.route('/kpis/<identifier>', methods=['DELETE'])
    def delete_kpi(identifier):
        """Delete a custom KPI by index or id"""
        custom = load_custom_kpis()
        try:
            idx = int(identifier)
            if 0 <= idx < len(custom):
                removed = custom.pop(idx)
                save_custom_kpis(custom)
                return jsonify({'status': 'removed', 'removed': removed})
        except Exception:
            pass

        # Try id match
        new = [k for k in custom if str(k.get('id')) != identifier]
        if len(new) != len(custom):
            save_custom_kpis(new)
            return jsonify({'status': 'removed_by_id', 'id': identifier})

        return jsonify({'error': 'not found'}), 404

    @app.route('/apply_edit', methods=['POST'])
    def apply_edit():
        """Apply a column edit (set or map) and return preview"""
        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'no payload'}), 400

        data_path = os.path.join(data_dir, 'Sample_Policy_Data.csv')
        if not os.path.exists(data_path):
            return jsonify({'error': 'input data not found'}), 404
        df = pd.read_csv(data_path)

        action = payload.get('action')
        if action == 'set_column':
            col = payload.get('column')
            val = payload.get('value')
            if col not in df.columns:
                return jsonify({'error': 'column not found'}), 400
            df[col] = val
        elif action == 'map_column':
            col = payload.get('column')
            mapping = payload.get('mapping', {})
            if col not in df.columns:
                return jsonify({'error': 'column not found'}), 400
            df[col] = df[col].astype(str).map(mapping).fillna(df[col])
        else:
            return jsonify({'error': 'unknown action'}), 400

        os.makedirs(output_dir, exist_ok=True)
        preview_path = os.path.join(output_dir, 'preview_edit.csv')
        df.to_csv(preview_path, index=False)
        return jsonify({'preview_rows': df.head(20).to_dict(orient='records')})

    @app.route('/chat', methods=['POST'])
    def chat():
        """Simple chat endpoint for quick suggestions"""
        payload = request.get_json() or {}
        message = payload.get('message', '')

        ollama = OllamaClient('http://localhost:11434')
        if ollama.available:
            try:
                interp = SemanticRuleInterpreter(ollama)
                suggestions = getattr(interp, 'suggest_remediations', lambda x: ['no suggestion'])(message)
                return jsonify({'ok': True, 'suggestions': suggestions})
            except Exception as e:
                logger.exception('LLM chat failed')
                return jsonify({'ok': False, 'error': str(e)}), 500

        # Fallback hints when LLM not available
        hints = {
            'fix dates': 'Open Rules, add a validity/consistency remediation with "parse_date" for date columns',
            'add kpi': 'Use the KPI editor to add a new KPI JSON and click Add',
            'preview': 'Use the Preview section to view first 10 cleaned rows'
        }
        resp = {
            'ok': True,
            'reply': hints.get(message.lower(), 'I can suggest remediations, KPI ideas, or run preview edits.')
        }
        return jsonify(resp)

    @app.route('/', methods=['GET'])
    def index():
        """Main dashboard UI"""
        html = '''
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>HITL Dashboard</title>
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
          <style>
            body { background: linear-gradient(135deg, #f8fafc, #eef2ff); }
            .card { box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08); border: none; }
            textarea { font-family: monospace; font-size: 0.85rem; }
            #preview-table { max-height: 400px; overflow-y: auto; }
            .badge { font-size: 0.9rem; }
            #log { font-family: monospace; font-size: 0.8rem; }
          </style>
        </head>
        <body>
        <div class="container py-4">
          <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
              <h2 class="mb-1">HITL Dashboard</h2>
              <small class="text-muted">Rule Editor, KPI Manager, Data Preview</small>
            </div>
            <div>
              <a class="btn btn-outline-primary me-2" href="/download" target="_blank">Download CSV</a>
              <a class="btn btn-outline-info" href="/validate_llm" target="_blank">Validate LLM</a>
            </div>
          </div>

          <div class="row g-3">
            <div class="col-lg-6">
              <div class="card p-4">
                <h5 class="card-title mb-3">Cleansing Rules</h5>
                <textarea id="rules" class="form-control mb-3" style="height:320px;" placeholder="JSON rules will load here..."></textarea>
                <div class="d-flex gap-2">
                  <button class="btn btn-sm btn-outline-secondary" onclick="loadRules()">Load Rules</button>
                  <button class="btn btn-sm btn-success" onclick="applyRules()">Apply Rules</button>
                </div>
                <small class="d-block mt-2 text-muted">Edit rules above and click Apply to re-run remediation and update the CSV.</small>
              </div>
            </div>

            <div class="col-lg-6">
              <div class="card p-4 mb-3">
                <h5 class="card-title mb-3">KPIs</h5>
                <div id="kpi-list" class="mb-3"></div>
                <div class="input-group input-group-sm mb-2">
                  <input id="new-kpi" class="form-control" placeholder='{"id":"k1","name":"Completeness"}'>
                  <button class="btn btn-primary" onclick="addKPI()">Add</button>
                </div>
                <small class="text-muted">Add custom KPIs from <code>data/DQ_Dashboard_KPIs.csv</code>.</small>
              </div>

              <div class="card p-4">
                <h5 class="card-title mb-3">Logs</h5>
                <pre id="log"></pre>
              </div>
            </div>
          </div>

          <div class="row mt-3">
            <div class="col-12">
              <div class="card p-4">
                <h5 class="card-title mb-3">Data Preview (first 10 cleaned rows)</h5>
                <div id="preview-table"></div>
              </div>
            </div>
          </div>
        </div>

        <script>
        function log(msg) {
            const p = document.getElementById("log");
            const ts = new Date().toLocaleTimeString();
            p.innerText = `[${ts}] ${msg}\\n` + (p.innerText || "");
            if (p.innerText.split("\\n").length > 50) {
                p.innerText = p.innerText.split("\\n").slice(0, 50).join("\\n");
            }
        }

        async function loadRules() {
            try {
                const r = await fetch("/rules");
                const txt = await r.text();
                const data = JSON.parse(txt);
                document.getElementById("rules").value = JSON.stringify(data, null, 2);
                log("Rules loaded from server");
            } catch (e) {
                log("Error loading rules: " + e.message);
            }
        }

        async function loadKPIs() {
            try {
                const r = await fetch("/kpis");
                const j = await r.json();
                const list = document.getElementById("kpi-list");
                list.innerHTML = "";

                (j.base_kpis || []).forEach(k => {
                    const el = document.createElement("span");
                    el.className = "badge bg-light text-dark p-2 me-2 mb-2";
                    el.innerText = k.name || k.id || JSON.stringify(k);
                    list.appendChild(el);
                });

                (j.custom_kpis || []).forEach((k, i) => {
                    const el = document.createElement("span");
                    el.className = "badge bg-info text-white p-2 me-2 mb-2";
                    el.innerHTML = (k.name || k.id || JSON.stringify(k)) + " <button class='btn btn-sm btn-link text-white ms-1 p-0' onclick='delKpi(" + i + ")'>x</button>";
                    list.appendChild(el);
                });
                log("KPIs loaded");
            } catch (e) {
                log("Error loading KPIs: " + e.message);
            }
        }

        async function addKPI() {
            const v = document.getElementById("new-kpi").value;
            try {
                const obj = JSON.parse(v);
                const r = await fetch("/kpis", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(obj)
                });
                const res = await r.json();
                log("KPI added");
                loadKPIs();
                document.getElementById("new-kpi").value = "";
            } catch (e) {
                log("Error adding KPI: " + e.message);
            }
        }

        async function delKpi(i) {
            try {
                await fetch("/kpis/" + i, { method: "DELETE" });
                log("KPI deleted");
                loadKPIs();
            } catch (e) {
                log("Error deleting KPI: " + e.message);
            }
        }

        async function applyRules() {
            const body = document.getElementById("rules").value;
            try {
                JSON.parse(body);
            } catch (e) {
                log("Rules must be valid JSON");
                return;
            }

            try {
                const r = await fetch("/apply", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: body
                });
                const j = await r.json();
                if (j.status === "success") {
                    log("Remediation applied. Rows: " + j.rows);
                    log("Changes per column: " + JSON.stringify(j.changes));
                    renderPreview(j.preview);
                } else {
                    log("Apply failed: " + JSON.stringify(j));
                }
            } catch (e) {
                log("Error applying rules: " + e.message);
            }
        }

        function renderPreview(rows) {
            if (!rows || rows.length === 0) {
                document.getElementById("preview-table").innerHTML = "<i>No preview data</i>";
                return;
            }
            const cols = Object.keys(rows[0]);
            let html = "<table class='table table-sm table-striped'><thead><tr>";
            cols.forEach(c => { html += "<th>" + c + "</th>"; });
            html += "</tr></thead><tbody>";
            rows.forEach(r => {
                html += "<tr>";
                cols.forEach(c => { html += "<td>" + (r[c] === null ? "" : String(r[c])) + "</td>"; });
                html += "</tr>";
            });
            html += "</tbody></table>";
            document.getElementById("preview-table").innerHTML = html;
        }

        // Initialize
        window.addEventListener("load", () => {
            loadRules();
            loadKPIs();
            log("Dashboard ready");
        });
        </script>
        </body>
        </html>
        '''
        return html

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
