using System.Diagnostics;

namespace DevHub;

public class ProcessManager
{
    private Process? _daemon;
    private Process? _caddy;
    private Process? _ui;
    private readonly string _devhubRoot;

    public ProcessManager(string devhubRoot) => _devhubRoot = devhubRoot;

    public void StartAll(int uiPort, string daemonToken)
    {
        // Stop any existing processes before starting new ones
        StopAll();

        try
        {
            _daemon = StartProcess(
                "python",
                "-m uvicorn daemon.main:app --host 127.0.0.1 --port 7477",
                _devhubRoot
            );
        }
        catch (Exception ex) { System.Diagnostics.Debug.WriteLine($"Daemon start failed: {ex.Message}"); }

        try
        {
            _caddy = StartProcess(
                System.IO.Path.Combine(_devhubRoot, "caddy.exe"),
                $"run --config \"{System.IO.Path.Combine(_devhubRoot, "Caddyfile")}\"",
                _devhubRoot
            );
        }
        catch (Exception ex) { System.Diagnostics.Debug.WriteLine($"Caddy start failed: {ex.Message}"); }

        try
        {
            _ui = StartProcess(
                "cmd.exe",
                $"/c npm run start -- --port {uiPort}",
                System.IO.Path.Combine(_devhubRoot, "ui"),
                new Dictionary<string, string> { ["DAEMON_TOKEN"] = daemonToken }
            );
        }
        catch (Exception ex) { System.Diagnostics.Debug.WriteLine($"UI start failed: {ex.Message}"); }
    }

    public void StopAll()
    {
        foreach (var p in new[] { _ui, _caddy, _daemon })
            TryKill(p);
    }

    public bool IsDaemonAlive() => _daemon is { HasExited: false };
    public bool IsCaddyAlive() => _caddy is { HasExited: false };
    public bool IsUiAlive() => _ui is { HasExited: false };

    public (bool daemon, bool caddy, bool ui) GetStatus() =>
        (IsDaemonAlive(), IsCaddyAlive(), IsUiAlive());

    private static Process StartProcess(string exe, string args, string workDir,
        Dictionary<string, string>? env = null)
    {
        var psi = new ProcessStartInfo(exe, args)
        {
            WorkingDirectory = workDir,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        if (env != null)
            foreach (var (k, v) in env)
                psi.Environment[k] = v;
        return Process.Start(psi) ?? throw new Exception($"Failed to start {exe}");
    }

    private static void TryKill(Process? p)
    {
        if (p == null) return;
        try { p.Kill(entireProcessTree: true); } catch { }
        try { p.Dispose(); } catch { }
    }
}
