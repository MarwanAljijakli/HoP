namespace DeceptionGPTDashboard.Models;

public class DashboardVm
{
    public List<SessionVm> ActiveSessions { get; set; } = new();
}


    public class SessionVm
    {
        public string SessionId { get; set; } = "";
        public string AttackerIp { get; set; } = "";
        public string Protocol { get; set; } = "SSH";
        public int CommandCount { get; set; }
        public string Status { get; set; } = "ACTIVE";
    }

