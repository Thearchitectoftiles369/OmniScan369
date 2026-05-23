import subprocess
import sys
import sqlite3
import asyncio
import random
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, List, Literal, Optional

try:
    import websockets
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])

app = FastAPI(title="OmniScan-369-Wellness-HRV-Platform")
DB_FILE = "omniscan.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            scan_date TEXT,
            vitality_score INTEGER DEFAULT 100,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            session_id INTEGER,
            log_text TEXT,
            is_anomaly INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(session_id) REFERENCES scan_sessions(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

BIO_SYSTEMS = [
    {"id": "brain", "name": "Brain Cortex", "x": 0.50, "y": 0.14, "side": "left"},
    {"id": "optic", "name": "Optic Nerve", "x": 0.52, "y": 0.17, "side": "right"},
    {"id": "thyroid", "name": "Thyroid Node", "x": 0.50, "y": 0.23, "side": "left"},
    {"id": "vagus", "name": "Vagus Nerve", "x": 0.47, "y": 0.28, "side": "left"},
    {"id": "lungs", "name": "Pulmonary Lungs", "x": 0.56, "y": 0.35, "side": "right"},
    {"id": "heart", "name": "Heart Anatomy", "x": 0.46, "y": 0.36, "side": "left"},
    {"id": "liver", "name": "Hepatic Liver", "x": 0.55, "y": 0.44, "side": "right"},
    {"id": "stomach", "name": "Gastric Stomach", "x": 0.44, "y": 0.46, "side": "left"},
    {"id": "kidneys", "name": "Renal Kidneys", "x": 0.50, "y": 0.53, "side": "right"}
]

class UserCommand(BaseModel):
    command: Literal["toggle-anomaly", "focus-node", "select-patient", "create-patient", "get-session-details"]
    node_name: Optional[str] = None
    patient_name: Optional[str] = None
    session_id: Optional[int] = None

def generate_wellness_telemetry(agent_name: str, force_anomaly: bool) -> tuple[str, bool]:
    if force_anomaly:
        hrv_ms = random.randint(15, 38)
        status_messages = [
            f"⚠️ Low HRV response in {agent_name}: {hrv_ms}ms. Cellular stress detected.",
            f"🚨 Sympathetic overload in {agent_name} at {hrv_ms}ms. Elevated cortisol markers.",
            f"📉 Reduced autonomic recovery for {agent_name}: {hrv_ms}ms. Fatigue alert."
        ]
        return random.choice(status_messages), True
    else:
        hrv_ms = random.randint(55, 95)
        status_messages = [
            f"💚 Homeostasis achieved for {agent_name}: {hrv_ms}ms (Optimal Vagus Tone).",
            f"✅ Balanced neural feedback in {agent_name}: {hrv_ms}ms. Parasympathetic stability.",
            f"✨ High recovery index for {agent_name}: {hrv_ms}ms. Systemic harmony."
        ]
        return random.choice(status_messages), False

class SimulationSession:
    def __init__(self):
        self.anomaly_active = False
        self.current_patient_id = None
        self.current_patient_name = "None"
        self.current_session_id = None
        self.agents = [{**system, "is_anomaly": False, "hrv": 75} for system in BIO_SYSTEMS]
        self.logs = [{"text": "⚛️ OmniScan Holographic Matrix Online. 3D Mesh Ready.", "is_anomaly": False}]
        self.session_scores = [] 

    def update_state(self):
        updated_log = False
        for agent in self.agents:
            old_state = agent["is_anomaly"]
            if self.anomaly_active:
                agent["is_anomaly"] = random.random() < 0.28
            else:
                agent["is_anomaly"] = False
            
            log_text, is_anom = generate_wellness_telemetry(agent["name"], agent["is_anomaly"])
            agent["hrv"] = random.randint(15, 38) if agent["is_anomaly"] else random.randint(55, 95)
            
            if agent["is_anomaly"] and not old_state and random.random() < 0.3:
                self.logs.append({"text": log_text, "is_anomaly": True})
                updated_log = True
                self.save_log_to_db(log_text, 1)
                
        if not updated_log and random.random() < 0.1:
            target = random.choice(self.agents)
            log_text, _ = generate_wellness_telemetry(target["name"], target["is_anomaly"])
            self.logs.append({"text": log_text, "is_anomaly": target["is_anomaly"]})
            self.save_log_to_db(log_text, 1 if target["is_anomaly"] else 0)
            
        if len(self.logs) > 20:
            self.logs = self.logs[-20:]

        if self.anomaly_active:
            self.session_scores.append(self.calculate_current_moment_score())

    def calculate_current_moment_score(self) -> int:
        anomalies = sum(1 for a in self.agents if a["is_anomaly"])
        score = 100 - (anomalies * 11)
        return max(score, 12)

    def get_display_score(self) -> int:
        if not self.anomaly_active:
            return 98
        if not self.session_scores:
            return 98
        return int(sum(self.session_scores) / len(self.session_scores))

    def start_new_scan_session(self):
        if self.current_patient_id:
            try:
                self.session_scores = []
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                cursor.execute("INSERT INTO scan_sessions (patient_id, scan_date, vitality_score) VALUES (?, ?, 100)", (self.current_patient_id, now_str))
                self.current_session_id = cursor.lastrowid
                conn.commit()
                conn.close()
            except Exception:
                pass

    def finalize_and_save_session_score(self):
        if self.current_patient_id and self.current_session_id:
            final_score = self.get_display_score()
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE scan_sessions SET vitality_score = ? WHERE id = ?", (final_score, self.current_session_id))
                conn.commit()
                conn.close()
            except Exception:
                pass

    def save_log_to_db(self, text: str, is_anom: int):
        if self.current_patient_id and self.current_session_id:
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO scan_logs (patient_id, session_id, log_text, is_anomaly) VALUES (?, ?, ?, ?)", (self.current_patient_id, self.current_session_id, text, is_anom))
                conn.commit()
                conn.close()
            except Exception:
                pass

    def to_dict(self) -> Dict[str, Any]:
        score = self.get_display_score()
        
        # ЛОГИКА ЗА ТЕРАПЕВТИЧНИ ИНСТРУКЦИИ
        if score < 75:
            instruction = "⚠️ ЗАСЕЧЕН СТРЕС: Вдишай дълбоко 2 пъти и издишай бавно за ресет на тялото."
        elif score < 90:
            instruction = "⚡ ЛЕКО НАПРЕЖЕНИЕ: Отпусни раменете и запази спокоен ритъм на дишане."
        else:
            instruction = "💚 ОПТИМАЛЕН БАЛАНС: Нервната система е в хомеостаза."

        return {
            "anomaly_active": self.anomaly_active,
            "patient_name": self.current_patient_name,
            "agents": self.agents,
            "logs": self.logs,
            "vitality_score": score,
            "instruction": instruction
        }

@app.get("/")
async def get_index():
    return HTMLResponse(content=HTML_CONTENT, status_code=200)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    session = SimulationSession()
    writer_task = asyncio.create_task(session_writer(websocket, session))
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM patients ORDER BY id DESC")
        patients = [row[0] for row in cursor.fetchall()]
        conn.close()
        await websocket.send_json({"type": "patients_list", "data": patients})
    except Exception:
        pass

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60.0)
                cmd = UserCommand(**data)
                
                if cmd.command == "toggle-anomaly":
                    if not session.anomaly_active:
                        session.anomaly_active = True
                        session.start_new_scan_session()
                        await send_patient_history(websocket, session.current_patient_id)
                    else:
                        session.finalize_and_save_session_score()
                        session.anomaly_active = False
                        await send_patient_history(websocket, session.current_patient_id)
                        session.current_session_id = None
                        
                elif cmd.command == "focus-node" and cmd.node_name:
                    msg = f"🔍 Focused Analysis: {cmd.node_name}."
                    session.logs.append({"text": msg, "is_anomaly": False})
                    session.save_log_to_db(msg, 0)
                    
                elif cmd.command == "create-patient" and cmd.patient_name:
                    name = cmd.patient_name.strip()
                    if name:
                        try:
                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()
                            cursor.execute("INSERT OR IGNORE INTO patients (name) VALUES (?)", (name,))
                            cursor.execute("SELECT id FROM patients WHERE name = ?", (name,))
                            p_id = cursor.fetchone()[0]
                            cursor.execute("SELECT name FROM patients ORDER BY id DESC")
                            all_patients = [row[0] for row in cursor.fetchall()]
                            conn.commit()
                            conn.close()
                            
                            session.current_patient_id = p_id
                            session.current_patient_name = name
                            session.current_session_id = None
                            session.logs.append({"text": f"👤 Profile Activated: {name}", "is_anomaly": False})
                            
                            await websocket.send_json({"type": "patients_list", "data": all_patients})
                            await websocket.send_json({"type": "state", "data": session.to_dict()})
                            await send_patient_history(websocket, p_id)
                        except Exception:
                            pass
                            
                elif cmd.command == "select-patient" and cmd.patient_name:
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM patients WHERE name = ?", (cmd.patient_name,))
                        row = cursor.fetchone()
                        if row:
                            session.current_patient_id = row[0]
                            session.current_patient_name = cmd.patient_name
                            session.current_session_id = None
                            session.logs.append({"text": f"👤 Profile switched to: {cmd.patient_name}", "is_anomaly": False})
                            await send_patient_history(websocket, row[0])
                        conn.close()
                    except Exception:
                        pass
                        
                elif cmd.command == "get-session-details" and cmd.session_id:
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("SELECT log_text, is_anomaly FROM scan_logs WHERE session_id = ? ORDER BY id ASC", (cmd.session_id,))
                        rows = cursor.fetchall()
                        cursor.execute("SELECT scan_date, vitality_score FROM scan_sessions WHERE id = ?", (cmd.session_id,))
                        session_row = cursor.fetchone()
                        conn.close()
                        archive_logs = [{"text": r[0], "is_anomaly": bool(r[1])} for r in rows]
                        await websocket.send_json({
                            "type": "archive_logs", 
                            "data": {"logs": archive_logs, "date": session_row[0], "score": session_row[1]}
                        })
                    except Exception:
                        pass
                        
            except ValidationError:
                await websocket.send_json({"type": "error", "message": "Validation Error"})
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        writer_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass

async def session_writer(websocket: WebSocket, session: SimulationSession):
    try:
        while True:
            session.update_state()
            await websocket.send_json({"type": "state", "data": session.to_dict()})
            await asyncio.sleep(1.2)
    except Exception:
        pass

async def send_patient_history(websocket: WebSocket, patient_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, scan_date, vitality_score FROM scan_sessions WHERE patient_id = ? ORDER BY id DESC", (patient_id,))
        history = [{"id": row[0], "date": row[1], "score": row[2]} for row in cursor.fetchall()]
        conn.close()
        await websocket.send_json({"type": "history_list", "data": history})
    except Exception:
        pass

HTML_CONTENT = """<!DOCTYPE html>
<html>
<head>
    <title>OmniScan 369 - Holographic Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body { margin: 0; background-color: #030307; color: #f1f5f9; font-family: monospace; overflow-x: hidden; display: flex; height: 100vh; }
        #view-container { width: 68vw; height: 100vh; background: radial-gradient(circle at 50% 45%, #05162e 0%, #010205 100%); position: relative; display: flex; justify-content: center; align-items: center; }
        canvas { background: transparent; display: block; }
        #sidebar { width: 32vw; height: 100vh; background-color: #020205; border-left: 1px solid #102445; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }
        
        .brand-box { border-left: 3px solid #00f0ff; padding-left: 10px; position: relative; }
        h1 { font-size: 15px; color: #00f0ff; margin: 0; letter-spacing: 1.5px; text-transform: uppercase; text-shadow: 0 0 8px rgba(0,240,255,0.4); }
        .subtitle { font-size: 9px; color: #64748b; margin-top: 2px; font-weight: bold; text-transform: uppercase; }
        .vitality-badge { position: absolute; right: 0; top: 0; background: #064e3b; color: #34d399; font-size: 12px; padding: 4px 8px; border-radius: 3px; font-weight: bold; border: 1px solid #047857; box-shadow: 0 0 10px rgba(52,211,153,0.2); }
        
        /* НОВИ СТИЛОВЕ ЗА ТЕРАПЕВТИЧНИЯ ПАНЕЛ */
        .instruction-box { padding: 10px; margin-top: 10px; font-size: 11px; border-radius: 4px; line-height: 1.4; text-align: center; font-weight: bold; transition: all 0.3s ease; }
        .instr-stress { color: #f87171; border: 1px solid #7f1d1d; background: #2a0a0a; animation: pulse-red 2s infinite; }
        .instr-warn { color: #fbbf24; border: 1px solid #b45309; background: #1f1406; }
        .instr-ok { color: #34d399; border: 1px solid #047857; background: #02120a; }
        @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); } 70% { box-shadow: 0 0 0 6px rgba(220, 38, 38, 0); } 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); } }

        .db-panel { background: #060d1a; border: 1px solid #102445; padding: 10px; border-radius: 4px; display: flex; flex-direction: column; gap: 8px; }
        .db-title { font-size: 11px; color: #38bdf8; font-weight: bold; }
        .patient-row { display: flex; gap: 5px; }
        input { background: #020612; border: 1px solid #142c54; color: #fff; padding: 6px; font-family: monospace; font-size: 11px; flex-grow: 1; border-radius: 3px; }
        select { background: #020612; border: 1px solid #142c54; color: #00f0ff; padding: 6px; font-family: monospace; font-size: 11px; width: 100%; border-radius: 3px; }
        .small-btn { background: #102445; border: none; color: #fff; padding: 6px 12px; cursor: pointer; font-family: monospace; font-size: 11px; border-radius: 3px; }
        .history-box { background: #020714; border: 1px solid #0f1f3d; max-height: 100px; overflow-y: auto; border-radius: 3px; padding: 4px; }
        .history-item { padding: 5px; font-size: 10px; border-bottom: 1px solid #091326; cursor: pointer; color: #94a3b8; display: flex; justify-content: space-between; }
        .history-item:hover { background: #0d1e3d; color: #fff; }
        
        button.main-btn { background: #002b3d; border: 1px solid #00f0ff; color: #00f0ff; padding: 14px; cursor: pointer; border-radius: 4px; font-weight: bold; width: 100%; font-size: 11px; letter-spacing: 1px; font-family: monospace; min-height: 45px; text-shadow: 0 0 5px rgba(0,240,255,0.5); box-shadow: 0 0 10px rgba(0,240,255,0.1); transition: all 0.2s ease; }
        button.main-btn.active { background: #7f1d1d; color: #ffffff; box-shadow: 0 0 20px #dc2626; border-color: #ef4444; text-shadow: none; }
        #logs-container { flex-grow: 1; min-height: 180px; overflow-y: auto; background: #010205; border: 1px solid #0b1629; padding: 12px; font-size: 11px; color: #00f0ff; border-radius: 4px; }
        .log-entry { margin-bottom: 8px; border-bottom: 1px solid #060d1a; padding-bottom: 6px; line-height: 1.4; }
        .log-anomaly { color: #f87171; border-left: 3px solid #dc2626; padding-left: 5px; }
        .active-patient-badge { font-size: 11px; color: #a7f3d0; background: #082f49; border: 1px solid #0369a1; padding: 4px 8px; border-radius: 3px; display: inline-block; margin-top: 4px;}
        
        #print-report-area { display: none; }
        @media print {
            body { background: #ffffff !important; color: #1e293b !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; display: block !important; }
            #sidebar, #view-container { display: none !important; }
            #print-report-area { display: block !important; background: #ffffff !important; color: #1e293b !important; padding: 40px; font-family: monospace; }
            .print-card { background: #f8fafc !important; border: 1px solid #cbd5e1 !important; color: #334155 !important; padding: 15px; border-radius: 4px; }
            .print-anomaly-line { color: #b91c1c !important; border-left: 3px solid #ef4444 !important; padding-left: 6px; margin-bottom: 6px; }
            .print-normal-line { color: #0f766e !important; border-left: 3px solid #10b981 !important; padding-left: 6px; margin-bottom: 6px; }
        }
        
        @media(max-width: 1024px) {
            body { flex-direction: column; height: auto; overflow-y: auto; }
            #view-container { width: 100vw; height: 55vh; min-height: 460px; }
            #sidebar { width: 100vw; height: auto; border-left: none; border-top: 1px solid #102445; }
        }
    </style>
</head>
<body>
    <div id="view-container">
        <canvas id="scanCanvas"></canvas>
    </div>
    <div id="sidebar">
        <div class="brand-box">
            <h1>OMNISCAN 369 3D</h1>
            <div class="subtitle">Bio-Resonance Hologram Matrix</div>
            <div id="active-patient" class="active-patient-badge">Patient: None</div>
            <div id="vitality-index" class="vitality-badge">ANS Tone: 98%</div>
            <div id="therapy-instruction" class="instruction-box instr-ok">Изчаква се анализ на пациента...</div>
        </div>
        <div class="db-panel">
            <div class="db-title">👤 CLIENT MANAGEMENT</div>
            <div class="patient-row">
                <input type="text" id="new-patient-name" placeholder="Enter client name...">
                <button class="small-btn" id="btn-add-patient">ADD</button>
            </div>
            <select id="patient-select"><option value="">-- Select Active Profile --</option></select>
            <div class="db-title" style="margin-top: 5px;">📜 WELLNESS ASSESSMENT HISTORY</div>
            <div class="history-box" id="history-container">
                <div style="font-size:10px; color:#475569; padding:5px;">No active client profile loaded.</div>
            </div>
        </div>
        <button id="btn-anomaly" class="main-btn">RUN BIO-ASSESSMENT</button>
        <div id="logs-container"><div class="log-entry">⚛️ 3D Hologram Engine Online...</div></div>
    </div>
    <div id="print-report-area"></div>
    <script>
        const canvas = document.getElementById('scanCanvas');
        const ctx = canvas.getContext('2d');
        const container = document.getElementById('view-container');
        const logsContainer = document.getElementById('logs-container');
        const anomBtn = document.getElementById('btn-anomaly');
        const addPatientBtn = document.getElementById('btn-add-patient');
        const newPatientInput = document.getElementById('new-patient-name');
        const patientSelect = document.getElementById('patient-select');
        const activePatientBadge = document.getElementById('active-patient');
        const vitalityIndexBox = document.getElementById('vitality-index');
        const historyContainer = document.getElementById('history-container');
        const printReportArea = document.getElementById('print-report-area');
        const therapyBox = document.getElementById('therapy-instruction'); // Референция към новия панел
        
        let currentAppState = { anomaly_active: false, patient_name: "None", agents: [], logs: [], vitality_score: 98, instruction: "" };
        let lastLoadedArchiveLogs = []; let lastLoadedArchiveDate = ""; let lastLoadedArchiveScore = 98;
        
        const human3DMesh = [
            {x: 0.50, y: 0.08}, {x: 0.53, y: 0.09}, {x: 0.55, y: 0.12}, {x: 0.55, y: 0.16}, 
            {x: 0.52, y: 0.19}, {x: 0.50, y: 0.20}, {x: 0.48, y: 0.19}, {x: 0.45, y: 0.16}, 
            {x: 0.45, y: 0.12}, {x: 0.47, y: 0.09}, {x: 0.50, y: 0.08},
            {x: 0.52, y: 0.20}, {x: 0.53, y: 0.23}, {x: 0.58, y: 0.25}, {x: 0.63, y: 0.27},
            {x: 0.65, y: 0.32}, {x: 0.67, y: 0.39}, {x: 0.68, y: 0.47}, {x: 0.69, y: 0.55}, 
            {x: 0.67, y: 0.58}, {x: 0.65, y: 0.56}, 
            {x: 0.65, y: 0.48}, {x: 0.63, y: 0.40}, {x: 0.60, y: 0.33},
            {x: 0.59, y: 0.38}, {x: 0.58, y: 0.45}, {x: 0.59, y: 0.52}, {x: 0.57, y: 0.56},
            {x: 0.56, y: 0.64}, {x: 0.55, y: 0.73}, {x: 0.53, y: 0.82}, {x: 0.52, y: 0.90}, 
            {x: 0.53, y: 0.94}, {x: 0.49, y: 0.94},
            {x: 0.49, y: 0.85}, {x: 0.51, y: 0.75}, {x: 0.52, y: 0.66}, {x: 0.50, y: 0.60},
            {x: 0.48, y: 0.66}, {x: 0.49, y: 0.75}, {x: 0.51, y: 0.85}, {x: 0.51, y: 0.94}, 
            {x: 0.47, y: 0.94}, {x: 0.48, y: 0.90}, {x: 0.47, y: 0.82}, {x: 0.45, y: 0.73}, 
            {x: 0.44, y: 0.64},
            {x: 0.43, y: 0.56}, {x: 0.41, y: 0.52}, {x: 0.42, y: 0.45}, {x: 0.41, y: 0.38},
            {x: 0.40, y: 0.33}, {x: 0.37, y: 0.40}, {x: 0.35, y: 0.48}, {x: 0.35, y: 0.56}, 
            {x: 0.33, y: 0.58}, {x: 0.31, y: 0.55}, {x: 0.32, y: 0.47}, {x: 0.33, y: 0.39}, 
            {x: 0.35, y: 0.32},
            {x: 0.37, y: 0.27}, {x: 0.42, y: 0.25}, {x: 0.47, y: 0.23}, {x: 0.48, y: 0.20}
        ];
        const innerAnatomyLines = [
            [{x: 0.43, y: 0.27}, {x: 0.50, y: 0.29}, {x: 0.57, y: 0.27}],
            [{x: 0.44, y: 0.33}, {x: 0.50, y: 0.34}, {x: 0.56, y: 0.33}],
            [{x: 0.50, y: 0.34}, {x: 0.50, y: 0.55}],
            [{x: 0.46, y: 0.40}, {x: 0.54, y: 0.40}],
            [{x: 0.46, y: 0.45}, {x: 0.54, y: 0.45}],
            [{x: 0.47, y: 0.50}, {x: 0.53, y: 0.50}],
            [{x: 0.45, y: 0.77}, {x: 0.48, y: 0.77}],
            [{x: 0.52, y: 0.77}, {x: 0.55, y: 0.77}]
        ];

        const clientId = crypto.randomUUID();
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let host = window.location.host; let path = window.location.pathname;
        let wsUrl = `${protocol}//${host}/ws/${clientId}`;
        if (path.includes('/embed/')) { wsUrl = `${protocol}//${host}${path.replace(/\/$/, '')}/ws/${clientId}`.replace(/([^:]\/)\/+/g, "$1"); }
        
        const ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
            const res = JSON.parse(event.data);
            if (res.type === "patients_list") updatePatientsDropdown(res.data);
            else if (res.type === "history_list") renderHistory(res.data);
            else if (res.type === "archive_logs") renderArchiveLogs(res.data.logs, res.data.date, res.data.score);
            else if (res.type === "state") {
                currentAppState = res.data;
                activePatientBadge.innerText = `Client: ${currentAppState.patient_name}`;
                vitalityIndexBox.innerText = `ANS Tone: ${currentAppState.vitality_score}%`;
                vitalityIndexBox.style.background = currentAppState.vitality_score < 50 ? "#7f1d1d" : "#064e3b";
                
                // ОБНОВЯВАНЕ НА ТЕРАПЕВТИЧНАТА ИНСТРУКЦИЯ И ЦВЕТОВЕТЕ
                if (currentAppState.instruction) {
                    therapyBox.innerText = currentAppState.instruction;
                    if (currentAppState.vitality_score < 75) {
                        therapyBox.className = "instruction-box instr-stress";
                    } else if (currentAppState.vitality_score < 90) {
                        therapyBox.className = "instruction-box instr-warn";
                    } else {
                        therapyBox.className = "instruction-box instr-ok";
                    }
                }
                
                if (currentAppState.patient_name !== "None") patientSelect.value = currentAppState.patient_name;
                renderLogs();
            }
        };
        function sendCommand(obj) { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj)); }
        function updatePatientsDropdown(list) { patientSelect.innerHTML = '<option value="">-- Select Active Profile --</option>' + list.map(p => `<option value="${p}">${p}</option>`).join(''); if (currentAppState.patient_name !== "None") patientSelect.value = currentAppState.patient_name; }
        function renderHistory(list) { if(list.length === 0) { historyContainer.innerHTML = '<div style="font-size:10px; color:#475569; padding:5px;">No past scans.</div>'; return; } historyContainer.innerHTML = list.map(h => `<div class="history-item" onclick="loadArchiveSession(${h.id})"><span>📅 ${h.date} (${h.score}%)</span><span style="color:#38bdf8;">⚡ Report</span></div>`).join(''); }
        function loadArchiveSession(id) { sendCommand({ command: "get-session-details", session_id: id }); }
        
        function renderArchiveLogs(logs, sessionDate, score) {
            lastLoadedArchiveLogs = logs; lastLoadedArchiveDate = sessionDate; lastLoadedArchiveScore = score;
            logsContainer.innerHTML = `<div style="color:#00f0ff; border-bottom:1px solid #00f0ff; padding-bottom:4px; margin-bottom:8px; display:flex; justify-content:space-between;"><span style="font-weight:bold;">📁 REPORT (${score}%)</span><button id="real-print-btn" style="background:#00f0ff; color:#000; border:none; padding:4px 8px; font-size:10px; cursor:pointer; font-weight:bold; border-radius:2px;">PRINT</button></div>` + logs.map(l => `<div class="log-entry ${l.is_anomaly ? 'log-anomaly' : ''}">${l.text}</div>`).join('');
            logsContainer.scrollTop = 0;
            document.getElementById('real-print-btn').addEventListener('click', triggerDirectPrint);
        }
        function triggerDirectPrint() {
            let logHTML = lastLoadedArchiveLogs.map(l => `<div class="${l.is_anomaly ? 'print-anomaly-line' : 'print-normal-line'}">${l.text}</div>`).join('');
            printReportArea.innerHTML = `
                <div style="border-left: 4px solid #00f0ff; padding-left: 15px; margin-bottom: 30px;">
                    <h2 style="margin:0; color:#0369a1; font-size:24px;">🧬 OMNISCAN 369 - BIO-WELLNESS REPORT</h2>
                    <p style="margin:5px 0; color:#64748b; font-size:12px;">Autonomic Nervous System & HRV Diagnostic Analytics</p>
                </div>
                <table style="width:100%; border-collapse:collapse; margin-bottom:30px; font-size:14px; color:#334155;">
                    <tr style="background:#f1f5f9;"><td style="padding:8px; font-weight:bold; width:160px;">CLIENT PROFILE:</td><td style="padding:8px; border-bottom:1px solid #e2e8f0;">${currentAppState.patient_name}</td></tr>
                    <tr><td style="padding:8px; font-weight:bold;">ASSESSMENT DATE:</td><td style="padding:8px; border-bottom:1px solid #e2e8f0;">${lastLoadedArchiveDate}</td></tr>
                    <tr style="background:#f8fafc;"><td style="padding:8px; font-weight:bold;">AUTONOMIC SCORE:</td><td style="padding:8px; border-bottom:1px solid #e2e8f0; color:#0369a1; font-weight:bold; font-size:16px;">${lastLoadedArchiveScore}% (ANS Tone)</td></tr>
                </table>
                <div class="print-card">${logHTML}</div>
            `;
            window.print();
        }
        addPatientBtn.addEventListener('click', () => { const val = newPatientInput.value.trim(); if(val) { sendCommand({ command: "create-patient", patient_name: val }); newPatientInput.value = ""; } });
        patientSelect.addEventListener('change', (e) => { if(e.target.value) sendCommand({ command: "select-patient", patient_name: e.target.value }); });
        function renderLogs() { if (!currentAppState.anomaly_active && logsContainer.innerHTML.includes("REPORT")) return; logsContainer.innerHTML = currentAppState.logs.map(l => `<div class="log-entry ${l.is_anomaly ? 'log-anomaly' : ''}">${l.text}</div>`).join(''); logsContainer.scrollTop = logsContainer.scrollHeight; }
        anomBtn.addEventListener('click', () => { sendCommand({ command: "toggle-anomaly" }); });

        let laserY = 0.0;
        let laserDirection = 1;
        function drawLoop() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const w = canvas.width; const h = canvas.height;
            const isAnomActive = currentAppState.anomaly_active;
            
            if (isAnomActive) {
                laserY += 0.008 * laserDirection;
                if (laserY > 0.95 || laserY < 0.05) laserDirection *= -1;
            } else {
                laserY = 0.0;
            }

            ctx.lineWidth = 2.2;
            ctx.shadowBlur = 15;
            ctx.shadowColor = isAnomActive ? 'rgba(239, 68, 68, 0.9)' : 'rgba(0, 240, 255, 0.9)';
            ctx.strokeStyle = isAnomActive ? '#ef4444' : '#00f0ff';
            
            ctx.beginPath();
            human3DMesh.forEach((pt, i) => {
                let targetX = pt.x * w;
                let targetY = pt.y * h;
                if (i === 0) ctx.moveTo(targetX, targetY);
                else ctx.lineTo(targetX, targetY);
            });
            ctx.closePath();
            ctx.stroke();

            ctx.lineWidth = 1.2;
            innerAnatomyLines.forEach(line => {
                ctx.beginPath();
                line.forEach((pt, i) => {
                    if (i === 0) ctx.moveTo(pt.x * w, pt.y * h);
                    else ctx.lineTo(pt.x * w, pt.y * h);
                });
                ctx.stroke();
            });
            
            ctx.shadowBlur = 0; 
            
            if (isAnomActive) {
                ctx.shadowBlur = 10;
                ctx.shadowColor = '#ef4444';
                ctx.strokeStyle = 'rgba(239, 68, 68, 0.8)';
                ctx.lineWidth = 2.5;
                ctx.beginPath();
                ctx.moveTo(w * 0.25, laserY * h);
                ctx.lineTo(w * 0.75, laserY * h);
                ctx.stroke();
                ctx.shadowBlur = 0;
            }
            
            if (currentAppState.agents) {
                const pulses = (Date.now() * 0.005);
                
                currentAppState.agents.forEach((agent, index) => {
                    let pointX = agent.x * w;
                    let pointY = agent.y * h;
                    
                    let radius = agent.is_anomaly ? 6.5 + Math.sin(pulses + index) * 2.5 : 5 + Math.sin(pulses * 0.5 + index) * 1.5;
                    
                    ctx.beginPath();
                    ctx.arc(pointX, pointY, radius + 4, 0, 2 * Math.PI);
                    ctx.fillStyle = agent.is_anomaly ? 'rgba(239, 68, 68, 0.25)' : 'rgba(0, 240, 255, 0.15)';
                    ctx.fill();
                    
                    ctx.beginPath();
                    ctx.arc(pointX, pointY, radius, 0, 2 * Math.PI);
                    ctx.fillStyle = agent.is_anomaly ? '#ef4444' : '#00f0ff';
                    ctx.fill();
                    
                    ctx.fillStyle = agent.is_anomaly ? '#f87171' : '#cbd5e1';
                    ctx.font = 'bold 11px monospace';
                    
                    let labelText = `${agent.name} [${agent.hrv}ms]`;
                    let labelY = 40 + (index * ((h - 70) / currentAppState.agents.length));
                    let labelX = agent.side === 'left' ? 20 : w - ctx.measureText(labelText).width - 20;
                    
                    ctx.beginPath();
                    ctx.strokeStyle = agent.is_anomaly ? 'rgba(239, 68, 68, 0.2)' : 'rgba(0, 240, 255, 0.15)';
                    ctx.lineWidth = 1;
                    ctx.moveTo(pointX, pointY);
                    ctx.lineTo(agent.side === 'left' ? labelX + 50 : labelX, labelY - 4);
                    ctx.stroke();
                    
                    ctx.fillText(labelText, labelX, labelY);
                });
            }
            anomBtn.className = isAnomActive ? 'main-btn active' : 'main-btn';
            anomBtn.innerText = isAnomActive ? "🚨 ANALYSIS IN PROGRESS..." : "RUN BIO-ASSESSMENT";
            
            requestAnimationFrame(drawLoop);
        }
        function resizeCanvas() {
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
        }
        
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        requestAnimationFrame(drawLoop);
    </script>
</body>
</html>
