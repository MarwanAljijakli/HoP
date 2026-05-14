using Microsoft.AspNetCore.Mvc;
using DeceptionGPTDashboard.Models;
using DeceptionGPTDashboard.Services;

namespace DeceptionGPTDashboard.Controllers
{
    public class HomeController : Controller
    {
        private readonly AiBackendClient _aiClient;

        public HomeController(AiBackendClient aiClient)
        {
            _aiClient = aiClient;
        }

        public async Task<IActionResult> Index(CancellationToken ct)
        {
            var events = await _aiClient.GetRecentEventsAsync(100, ct);

            var sessions = events
                .GroupBy(e => e.SessionId ?? "unknown")
                .Select(g => new SessionVm
                {
                    SessionId = g.Key,
                    AttackerIp = g.Select(e => e.SrcIp)
                                  .FirstOrDefault(s => !string.IsNullOrEmpty(s)) ?? "0.0.0.0",
                    CommandCount = g.Count(),
                })
                .ToList();

            var model = new DashboardVm { ActiveSessions = sessions };
            return View(model);
        }
    }
}
