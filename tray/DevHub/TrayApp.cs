using DevHub.Models;
using System.Diagnostics;

namespace DevHub;

public class TrayApp : ApplicationContext
{
    private readonly NotifyIcon _tray;
    private readonly ProcessManager _processes;
    private readonly DaemonClient _client;
    private readonly System.Windows.Forms.Timer _timer;
    private readonly AppConfig _config;
    private int _backoffMs = 250;
    private bool _daemonReady = false;
    private readonly string _devhubRoot;

    public TrayApp(string devhubRoot)
    {
        _devhubRoot = devhubRoot;
        _config = AppConfig.Load(devhubRoot);
        _processes = new ProcessManager(devhubRoot);
        _client = new DaemonClient(_config.DaemonToken);

        _tray = new NotifyIcon
        {
            Icon = SystemIcons.Application,
            Text = "DevHub — Starting...",
            Visible = true,
            ContextMenuStrip = BuildMenu([]),
        };

        _timer = new System.Windows.Forms.Timer { Interval = _backoffMs };
        _timer.Tick += OnTick;
        _timer.Start();

        _processes.StartAll(_config.UiPort, _config.DaemonToken);
    }

    private async void OnTick(object? sender, EventArgs e)
    {
        _timer.Stop();

        if (!_daemonReady)
        {
            // Exponential backoff until daemon is up: 250ms → 500ms → 1s → 2s
            var status = await _client.GetStatusAsync();
            if (status != null)
            {
                _daemonReady = true;
                _timer.Interval = 5000;
                _tray.Text = "DevHub";
                ToastHelper.Notify("DevHub", "Dev hub is ready.");
            }
            else
            {
                _backoffMs = Math.Min(_backoffMs * 2, 2000);
                _timer.Interval = _backoffMs;
            }
        }
        else
        {
            await RefreshAsync();
        }

        _timer.Start();
    }

    private async Task RefreshAsync()
    {
        var projects = await _client.GetProjectsAsync();
        var status = await _client.GetStatusAsync();

        // Check managed processes for crashes and restart
        var (daemon, caddy, ui) = _processes.GetStatus();
        if (!daemon)
        {
            _processes.StartAll(_config.UiPort, _config.DaemonToken);
            ToastHelper.Notify("DevHub", "Daemon crashed — restarting.");
            _daemonReady = false;
            _backoffMs = 250;
            _timer.Interval = _backoffMs;
        }

        // Update tray icon based on warnings
        bool hasWarnings = status?.Warnings?.Length > 0 || !daemon;
        _tray.Icon = hasWarnings ? SystemIcons.Warning : SystemIcons.Application;
        _tray.Text = hasWarnings ? "DevHub — Warning" : "DevHub";
        var oldMenu = _tray.ContextMenuStrip;
        _tray.ContextMenuStrip = BuildMenu(projects);
        oldMenu?.Dispose();
    }

    private ContextMenuStrip BuildMenu(List<Project> projects)
    {
        var menu = new ContextMenuStrip();

        // Open dashboard
        menu.Items.Add("Open Dashboard", null, (_, _) =>
            Process.Start(new ProcessStartInfo("http://devhub.localhost") { UseShellExecute = true }));

        menu.Items.Add(new ToolStripSeparator());

        // Project list
        foreach (var p in projects)
        {
            var label = $"{p.Name}  [{p.Status}]";
            var sub = new ToolStripMenuItem(label);

            sub.DropDownItems.Add("Start", null, async (_, _) =>
                await _client.StartProjectAsync(p.Id));
            sub.DropDownItems.Add("Stop", null, async (_, _) =>
                await _client.StopProjectAsync(p.Id));

            if (p.K3sAppName != null)
                sub.DropDownItems.Add("Deploy to dev", null, async (_, _) =>
                    await _client.DeployProjectAsync(p.Id));

            if (p.K3sAppName != null)
                sub.DropDownItems.Add("Promote to prod", null, async (_, _) =>
                    await _client.PromoteProjectAsync(p.Id));

            if (p.Port.HasValue)
                sub.DropDownItems.Add("Open in browser", null, (_, _) =>
                    Process.Start(new ProcessStartInfo($"http://localhost:{p.Port}") { UseShellExecute = true }));

            menu.Items.Add(sub);
        }

        if (projects.Count == 0)
        {
            var empty = new ToolStripMenuItem("(no projects)") { Enabled = false };
            menu.Items.Add(empty);
        }

        menu.Items.Add(new ToolStripSeparator());

        // Run at startup toggle
        bool startupEnabled = StartupHelper.IsEnabled();
        var startupItem = new ToolStripMenuItem("Run at Startup")
        {
            Checked = startupEnabled,
            CheckOnClick = true,
        };
        startupItem.Click += (_, _) =>
        {
            if (StartupHelper.IsEnabled())
                StartupHelper.Disable();
            else
                StartupHelper.Enable(Application.ExecutablePath);
        };
        menu.Items.Add(startupItem);

        menu.Items.Add(new ToolStripSeparator());

        // Quit
        menu.Items.Add("Quit", null, (_, _) =>
        {
            _processes.StopAll();
            _tray.Visible = false;
            Application.Exit();
        });

        return menu;
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _tray.Dispose();
            _timer.Dispose();
            _client.Dispose();
        }
        base.Dispose(disposing);
    }
}
