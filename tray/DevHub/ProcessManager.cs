using System.Diagnostics;

namespace DevHub;

public class ProcessManager
{
    private Process? _daemon;
    private Process? _caddy;
    private Process? _ui;
    private readonly string _devhubRoot;

    public ProcessManager(string devhubRoot) => _devhubRoot = devhubRoot;

    public void StartAll(int uiPort)
    {
        _daemon = StartProcess(
            "python",
            $"\"{System.IO.Path.Combine(_devhubRoot, "daemon", "main.py")}\"",
            _devhubRoot
        );
        _caddy = StartProcess(
            System.IO.Path.Combine(_devhubRoot, "caddy.exe"),
            $"run --config \"{System.IO.Path.Combine(_devhubRoot, "Caddyfile")}\"",
            _devhubRoot
        );
        _ui = StartProcess(
            "npm",
            $"run start -- --port {uiPort}",
            System.IO.Path.Combine(_devhubRoot, "ui")
        );
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

    private static Process StartProcess(string exe, string args, string workDir)
    {
        var psi = new ProcessStartInfo(exe, args)
        {
            WorkingDirectory = workDir,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        return Process.Start(psi) ?? throw new Exception($"Failed to start {exe}");
    }

    private static void TryKill(Process? p)
    {
        try { p?.Kill(entireProcessTree: true); } catch { }
    }
}
