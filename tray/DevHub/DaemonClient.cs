using System.Net.Http.Headers;
using System.Text.Json;
using DevHub.Models;

namespace DevHub;

public class DaemonClient : IDisposable
{
    private readonly HttpClient _http;
    private static readonly JsonSerializerOptions _opts = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public DaemonClient(string token)
    {
        _http = new HttpClient { BaseAddress = new Uri("http://localhost:7477/") };
        _http.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", token);
        _http.Timeout = TimeSpan.FromSeconds(5);
    }

    public async Task<DaemonStatus?> GetStatusAsync()
    {
        try
        {
            var json = await _http.GetStringAsync("status");
            return JsonSerializer.Deserialize<DaemonStatus>(json, _opts);
        }
        catch { return null; }
    }

    public async Task<List<Project>> GetProjectsAsync()
    {
        try
        {
            var json = await _http.GetStringAsync("projects");
            return JsonSerializer.Deserialize<List<Project>>(json, _opts) ?? [];
        }
        catch { return []; }
    }

    public async Task<bool> StartProjectAsync(string id)
    {
        try
        {
            var r = await _http.PostAsync($"projects/{id}/start", null);
            return r.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    public async Task<bool> StopProjectAsync(string id)
    {
        try
        {
            var r = await _http.PostAsync($"projects/{id}/stop", null);
            return r.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    public async Task<bool> DeployProjectAsync(string id)
    {
        try
        {
            var r = await _http.PostAsync($"projects/{id}/deploy", null);
            return r.IsSuccessStatusCode;
        }
        catch { return false; }
    }

    public void Dispose() => _http.Dispose();
}
