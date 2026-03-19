using System.Text.Json;
using System.Text.Json.Serialization;

namespace DevHub;

public class AppConfig
{
    [JsonPropertyName("daemon_token")] public string DaemonToken { get; set; } = "";
    [JsonPropertyName("ui_port")] public int UiPort { get; set; } = 3000;
    [JsonPropertyName("gitea_url")] public string GiteaUrl { get; set; } = "";

    public static AppConfig Load(string devhubRoot)
    {
        var path = System.IO.Path.Combine(devhubRoot, "daemon", "config.json");
        if (!System.IO.File.Exists(path)) return new AppConfig();
        try
        {
            var json = System.IO.File.ReadAllText(path);
            return JsonSerializer.Deserialize<AppConfig>(json) ?? new AppConfig();
        }
        catch
        {
            return new AppConfig();
        }
    }
}
