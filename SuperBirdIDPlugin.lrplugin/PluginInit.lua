local LrLogger = import 'LrLogger'

local myLogger = LrLogger( 'SuperBirdIDPlugin' )
myLogger:enable( "logfile" )

myLogger:info( "🦆 SuperBirdID 本地鸟类识别插件初始化完成 - v2.0.0" )