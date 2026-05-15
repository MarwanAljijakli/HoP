using Microsoft.AspNetCore.Mvc;
using DeceptionGPTDashboard.Models;
using DeceptionGPTDashboard.Services;

namespace DeceptionGPTDashboard.Controllers
{
    [ApiController]
    [Route("api")]
    public class ApiController : ControllerBase
    {
        private readonly AiBackendClient _client;

        public ApiController(AiBackendClient client)
        {
            _client = client;
        }

        [HttpGet("events")]
        public async Task<IActionResult> Events(CancellationToken ct)
        {
            Response.Headers["Cache-Control"] = "no-store";
            try
            {
                var events = await _client.GetRecentEventsAsync(200, ct);
                return new JsonResult(events);
            }
            catch
            {
                return new JsonResult(System.Array.Empty<EventDto>());
            }
        }
    }
}
