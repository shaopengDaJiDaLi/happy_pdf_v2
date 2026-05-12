import { PdfWorkspace } from "../components/PdfWorkspace";
import { ControlPanel } from "../components/ControlPanel";
import { LeftPanel } from "../components/LeftPanel";
import { useJobStream } from "../hooks/useJobStream";
import { useAppStore } from "../store/appStore";

export default function App() {
  const jobId = useAppStore((state) => state.job?.job_id);
  useJobStream(jobId);

  return (
    <main className="appShell">
      <header className="appHeader">
        <div>
          <h1>happy_pdf</h1>
          <p>扫描件 PDF 局部智能编辑工具</p>
        </div>
      </header>
      <div className="mainGrid">
        <LeftPanel />
        <PdfWorkspace />
        <ControlPanel />
      </div>
    </main>
  );
}
