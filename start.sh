#!/bin/zsh
# ReachALL 后端管理脚本
# 用法:
#   ./start.sh          — 前台启动（看日志）
#   ./start.sh start    — 后台启动
#   ./start.sh stop     — 停止后台进程
#   ./start.sh restart  — 重启后台进程
#   ./start.sh status   — 查看运行状态

PYTHON="/Users/ice/.local/pipx/venvs/agent-reach/bin/python"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.server.pid"
LOG_FILE="$SCRIPT_DIR/.server.log"
PORT=8765

_is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

_start_bg() {
  if _is_running; then
    echo "Already running (PID $(cat "$PID_FILE"))"
    return
  fi
  cd "$SCRIPT_DIR"
  nohup "$PYTHON" server.py >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  sleep 1
  if _is_running; then
    echo "Started  →  http://localhost:$PORT  (PID $(cat "$PID_FILE"))"
    echo "Logs     →  $LOG_FILE"
  else
    echo "Failed to start. Check $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
  fi
}

_stop() {
  if ! _is_running; then
    echo "Not running"
    rm -f "$PID_FILE"
    return
  fi
  PID=$(cat "$PID_FILE")
  kill "$PID" 2>/dev/null
  sleep 1
  if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID" 2>/dev/null
  fi
  rm -f "$PID_FILE"
  echo "Stopped (PID $PID)"
}

_status() {
  if _is_running; then
    PID=$(cat "$PID_FILE")
    echo "Running  →  PID $PID  →  http://localhost:$PORT"
    # quick health check
    if curl -s --max-time 2 "http://localhost:$PORT/api/health" | grep -q '"ok":true'; then
      echo "Health   →  OK"
    else
      echo "Health   →  not responding yet"
    fi
  else
    echo "Stopped"
    [[ -f "$PID_FILE" ]] && rm -f "$PID_FILE"
  fi
}

case "${1:-fg}" in
  start)    _start_bg ;;
  stop)     _stop ;;
  restart)  _stop; sleep 1; _start_bg ;;
  status)   _status ;;
  fg|"")
    echo "ReachALL server starting on http://localhost:$PORT  (Ctrl+C to stop)"
    cd "$SCRIPT_DIR"
    exec "$PYTHON" server.py
    ;;
  *)
    echo "Usage: $0 [start|stop|restart|status]"
    exit 1
    ;;
esac
