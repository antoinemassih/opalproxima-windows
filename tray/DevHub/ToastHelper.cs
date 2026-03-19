using Microsoft.Toolkit.Uwp.Notifications;

namespace DevHub;

public static class ToastHelper
{
    public static void Notify(string title, string message)
    {
        try
        {
            new ToastContentBuilder()
                .AddText(title)
                .AddText(message)
                .Show();
        }
        catch
        {
            // Toast not available in all Windows versions — fail silently
        }
    }
}
