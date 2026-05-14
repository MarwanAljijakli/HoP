using System.Net.Http.Json;
using DeceptionGPTDashboard.Models;

namespace DeceptionGPTDashboard.Services;

public class AiBackendClient
{
    private readonly HttpClient _http;
    private readonly ILogger<AiBackendClient> _logger;

    public AiBackendClient(HttpClient http, ILogger<AiBackendClient> logger)
    {
        _http = http;
        _logger = logger;
    }

    public async Task<IReadOnlyList<EventDto>> GetRecentEventsAsync(int limit, CancellationToken ct)
    {
        try
        {
            var resp = await _http.GetAsync($"/api/events?limit={limit}", ct);
            if (!resp.IsSuccessStatusCode)
            {
                _logger.LogWarning("AI backend /api/events returned {Status}", resp.StatusCode);
                return Array.Empty<EventDto>();
            }
            var events = await resp.Content.ReadFromJsonAsync<List<EventDto>>(cancellationToken: ct);
            return events ?? new List<EventDto>();
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "AI backend /api/events call failed");
            return Array.Empty<EventDto>();
        }
    }
}
