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
// In dev, walk up from the exe location until we find Caddyfile (the root marker)
var root = Environment.GetEnvironmentVariable("DEVHUB_ROOT");
if (root == null)
{
    var dir = new DirectoryInfo(AppContext.BaseDirectory);
    while (dir != null)
    {
        if (File.Exists(Path.Combine(dir.FullName, "Caddyfile")))
        {
            root = dir.FullName;
            break;
        }
        dir = dir.Parent;
    }
    root ??= AppContext.BaseDirectory;
}

Application.Run(new TrayApp(root));

mutex.ReleaseMutex();
