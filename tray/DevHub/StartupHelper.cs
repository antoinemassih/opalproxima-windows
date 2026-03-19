using Microsoft.Win32;

namespace DevHub;

public static class StartupHelper
{
    private const string KeyPath = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Run";
    private const string ValueName = "DevHub";

    public static void Enable(string exePath)
    {
        using var key = Registry.CurrentUser.OpenSubKey(KeyPath, true);
        key?.SetValue(ValueName, $"\"{exePath}\"");
    }

    public static void Disable()
    {
        using var key = Registry.CurrentUser.OpenSubKey(KeyPath, true);
        key?.DeleteValue(ValueName, false);
    }

    public static bool IsEnabled()
    {
        using var key = Registry.CurrentUser.OpenSubKey(KeyPath, false);
        return key?.GetValue(ValueName) != null;
    }
}
