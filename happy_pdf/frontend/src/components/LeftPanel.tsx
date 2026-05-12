import { useEffect, useMemo, useRef } from "react";
import { AlertCircle, ClipboardList, TerminalSquare } from "lucide-react";
import { useAppStore } from "../store/appStore";

export function LeftPanel() {
  const job = useAppStore((state) => state.job);
  const error = useAppStore((state) => state.error);
  const hasFailure =
    job?.status === "failed" ||
    job?.steps.some((step) => step.status === "failed") ||
    Boolean(error);

  return (
    <aside className="leftPanel">
      <section className="panelBlock guideBlock">
        <div className="panelTitle iconTitle">
          <ClipboardList size={16} />
          使用说明
        </div>
        <ol className="guideList">
          <li>上传扫描版 PDF。</li>
          <li>在页面中拖拽框选需要修改的局部区域。</li>
          <li>输入短指令，例如“日期改成 2026.12.11”或“把 300 改成 150”。</li>
          <li>点击“生成修改”，等待预览结果。</li>
          <li>确认无误后点击“应用到 PDF”。</li>
          <li>点击“导出 PDF”下载 edited.pdf。</li>
        </ol>
      </section>

      <LogPanel
        logs={job?.logs ?? []}
        hasFailure={hasFailure}
        latestError={error}
      />
    </aside>
  );
}

function LogPanel({
  logs,
  hasFailure,
  latestError
}: {
  logs: { time: string; message: string }[];
  hasFailure: boolean;
  latestError?: string;
}) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const retryMessage = useMemo(() => {
    if (!hasFailure) return undefined;
    const detail = latestError ? `错误信息：${latestError}。` : "";
    return `${detail}请检查 PDF、选区和修改指令后重新操作。`;
  }, [hasFailure, latestError]);

  useEffect(() => {
    const list = listRef.current;
    if (list) {
      list.scrollTop = list.scrollHeight;
    }
  }, [logs, retryMessage]);

  return (
    <section className="panelBlock logsBlock leftLogsBlock">
      <div className="panelTitle iconTitle">
        <TerminalSquare size={16} />
        执行日志
      </div>
      <div className="logList leftLogList" ref={listRef}>
        {logs.length === 0 && <div className="muted darkMuted">暂无日志</div>}
        {logs.map((log, index) => (
          <div className="logLine" key={`${log.time}-${index}`}>
            <span>[{log.time}]</span>
            <span>{log.message}</span>
          </div>
        ))}
        {retryMessage && (
          <div className="logLine retryLogLine">
            <span>
              <AlertCircle size={13} />
            </span>
            <span>{retryMessage}</span>
          </div>
        )}
      </div>
    </section>
  );
}
