return {
    LrSdkVersion = 11.0,
    LrSdkMinimumVersion = 8.0,

    LrToolkitIdentifier = 'com.superbirdid.lightroom',
    LrPluginName = "🦆 SuperBirdID 本地鸟类识别",

    LrInitPlugin = 'PluginInit.lua',

    LrExportServiceProvider = {
        {
            title = "🦆 SuperBirdID 本地鸟类识别",
            file = 'SuperBirdIDExportServiceProvider.lua',
        },
    },

    VERSION = { major=3, minor=2, revision=1, build=1, },
}
