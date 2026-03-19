using System.Text.Json.Serialization;

namespace DevHub.Models;

public record Project(
    string Id,
    string Name,
    string Path,
    string Type,
    string Status,
    int? Port,
    [property: JsonPropertyName("k3s_app_name")] string? K3sAppName,
    [property: JsonPropertyName("process_pid")] int? ProcessPid
);
