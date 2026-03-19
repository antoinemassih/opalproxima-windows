using DevHub;

// Single-instance guard via named Mutex
var mutex = new Mutex(true, "DevHub_SingleInstance_OpalProxima", out var isNew);
if (!isNew)
{
    MessageBox.Show(
        "DevHub is already running.",
        "DevHub",
        MessageBoxButtons.OK,
        MessageBoxIcon.Information
    );
    return;
}

Application.EnableVisualStyles();
Application.SetCompatibleTextRenderingDefault(false);

// devhub root: in release, DevHub.exe is at the zip root alongside daemon\ and ui\
// In dev, set DEVHUB_ROOT env var to override (e.g., set to the repo root)
var root = Environment.GetEnvironmentVariable("DEVHUB_ROOT")
    ?? AppContext.BaseDirectory;

Application.Run(new TrayApp(root));

mutex.ReleaseMutex();
