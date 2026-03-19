namespace DevHub.Models;

public record Project(
    string Id,
    string Name,
    string Path,
    string Type,
    string Status,
    int? Port,
    string? K3sAppName,
    int? ProcessPid
);
