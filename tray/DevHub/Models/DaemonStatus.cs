namespace DevHub.Models;

public record DaemonStatus(
    bool Ok,
    int ProjectsRunning,
    bool K8sAvailable,
    bool GiteaAvailable,
    string[] Warnings
);
