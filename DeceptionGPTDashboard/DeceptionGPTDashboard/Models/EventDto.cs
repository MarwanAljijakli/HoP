using System.Text.Json.Serialization;

namespace DeceptionGPTDashboard.Models;

public class EventDto
{
    [JsonPropertyName("timestamp")]
    public string? Timestamp { get; set; }

    [JsonPropertyName("session_id")]
    public string? SessionId { get; set; }

    [JsonPropertyName("src_ip")]
    public string? SrcIp { get; set; }

    [JsonPropertyName("input")]
    public string? Input { get; set; }

    [JsonPropertyName("response")]
    public string? Response { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("temperature")]
    public string? Temperature { get; set; }
}
