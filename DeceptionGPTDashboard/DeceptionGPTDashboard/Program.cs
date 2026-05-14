using DeceptionGPTDashboard.Models;
using DeceptionGPTDashboard.Services;
using Microsoft.Extensions.Options;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllersWithViews();

builder.Services.Configure<AiBackendOptions>(builder.Configuration.GetSection("AiBackend"));
builder.Services.AddHttpClient<AiBackendClient>((sp, c) =>
{
    c.BaseAddress = new Uri(sp.GetRequiredService<IOptions<AiBackendOptions>>().Value.BaseUrl);
    c.Timeout = TimeSpan.FromSeconds(5);
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

if (!app.Environment.IsDevelopment())
{
    app.UseHttpsRedirection();
}
app.UseRouting();

app.UseAuthorization();

app.MapStaticAssets();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");


    
app.Run();
