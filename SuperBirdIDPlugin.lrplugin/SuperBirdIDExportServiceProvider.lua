local LrTasks = import 'LrTasks'
local LrApplication = import 'LrApplication'
local LrDialogs = import 'LrDialogs'
local LrLogger = import 'LrLogger'
local LrHttp = import 'LrHttp'
local LrPathUtils = import 'LrPathUtils'
local LrFileUtils = import 'LrFileUtils'
local LrView = import 'LrView'
local LrBinding = import 'LrBinding'

-- 版本信息
local VERSION = "v2.0.0 - SuperBirdID本地版"

local myLogger = LrLogger( 'SuperBirdIDExportServiceProvider' )
myLogger:enable( "logfile" )

-- Binding helper
local bind = LrView.bind

-- Export service provider definition
local exportServiceProvider = {}

-- Required functions for Lightroom SDK
exportServiceProvider.supportsIncrementalPublish = false
exportServiceProvider.canExportVideo = false
exportServiceProvider.exportPresetDestination = "temp"

-- 不需要导出图片，只需获取原图路径
exportServiceProvider.allowFileFormats = nil
exportServiceProvider.allowColorSpaces = nil
exportServiceProvider.hideSections = { 'exportLocation', 'fileNaming', 'fileSettings', 'imageSettings', 'outputSharpening', 'metadata', 'watermarking' }

exportServiceProvider.exportPresetFields = {
    { key = 'apiUrl', default = "http://127.0.0.1:5156" },
    { key = 'topK', default = 3 },
    { key = 'useYolo', default = true },
    { key = 'useGps', default = true },
    { key = 'writeExif', default = true },
}

-- 完整国家列表 (保留用于显示，但不再需要预设国家代码)
local commonCountries = {
    { code = "AF", name = "阿富汗 (Afghanistan)" },
    { code = "AX", name = "奥兰群岛 (Åland Islands)" },
    { code = "AL", name = "阿尔巴尼亚 (Albania)" },
    { code = "DZ", name = "阿尔及利亚 (Algeria)" },
    { code = "AS", name = "美属萨摩亚 (American Samoa)" },
    { code = "AD", name = "安道尔 (AndorrA)" },
    { code = "AO", name = "安哥拉 (Angola)" },
    { code = "AI", name = "安圭拉 (Anguilla)" },
    { code = "AQ", name = "南极洲 (Antarctica)" },
    { code = "AG", name = "安提瓜和巴布达 (Antigua and Barbuda)" },
    { code = "AR", name = "阿根廷 (Argentina)" },
    { code = "AM", name = "亚美尼亚 (Armenia)" },
    { code = "AW", name = "阿鲁巴 (Aruba)" },
    { code = "AU", name = "澳大利亚 (Australia)" },
    { code = "AT", name = "奥地利 (Austria)" },
    { code = "AZ", name = "阿塞拜疆 (Azerbaijan)" },
    { code = "BS", name = "巴哈马 (Bahamas)" },
    { code = "BH", name = "巴林 (Bahrain)" },
    { code = "BD", name = "孟加拉国 (Bangladesh)" },
    { code = "BB", name = "巴巴多斯 (Barbados)" },
    { code = "BY", name = "白俄罗斯 (Belarus)" },
    { code = "BE", name = "比利时 (Belgium)" },
    { code = "BZ", name = "伯利兹 (Belize)" },
    { code = "BJ", name = "贝宁 (Benin)" },
    { code = "BM", name = "百慕大 (Bermuda)" },
    { code = "BT", name = "不丹 (Bhutan)" },
    { code = "BO", name = "玻利维亚 (Bolivia)" },
    { code = "BA", name = "波斯尼亚和黑塞哥维那 (Bosnia and Herzegovina)" },
    { code = "BW", name = "博茨瓦纳 (Botswana)" },
    { code = "BV", name = "布维岛 (Bouvet Island)" },
    { code = "BR", name = "巴西 (Brazil)" },
    { code = "IO", name = "英属印度洋领地 (British Indian Ocean Territory)" },
    { code = "BN", name = "文莱 (Brunei Darussalam)" },
    { code = "BG", name = "保加利亚 (Bulgaria)" },
    { code = "BF", name = "布基纳法索 (Burkina Faso)" },
    { code = "BI", name = "布隆迪 (Burundi)" },
    { code = "KH", name = "柬埔寨 (Cambodia)" },
    { code = "CM", name = "喀麦隆 (Cameroon)" },
    { code = "CA", name = "加拿大 (Canada)" },
    { code = "CV", name = "維德角 (Cape Verde)" },
    { code = "KY", name = "开曼群岛 (Cayman Islands)" },
    { code = "CF", name = "中非共和国 (Central African Republic)" },
    { code = "TD", name = "乍得 (Chad)" },
    { code = "CL", name = "智利 (Chile)" },
    { code = "CN", name = "中国 (China)" },
    { code = "CX", name = "圣诞岛 (Christmas Island)" },
    { code = "CC", name = "科科斯（基林）群岛 (Cocos (Keeling) Islands)" },
    { code = "CO", name = "哥伦比亚 (Colombia)" },
    { code = "KM", name = "科摩罗 (Comoros)" },
    { code = "CG", name = "刚果（布） (Congo)" },
    { code = "CD", name = "刚果民主共和国 (Congo, The Democratic Republic of the)" },
    { code = "CK", name = "库克群岛 (Cook Islands)" },
    { code = "CR", name = "哥斯达黎加 (Costa Rica)" },
    { code = "CI", name = "象牙海岸 (Cote D'Ivoire)" },
    { code = "HR", name = "克罗地亚 (Croatia)" },
    { code = "CU", name = "古巴 (Cuba)" },
    { code = "CY", name = "塞浦路斯 (Cyprus)" },
    { code = "CZ", name = "捷克 (Czech Republic)" },
    { code = "DK", name = "丹麦 (Denmark)" },
    { code = "DJ", name = "吉布提 (Djibouti)" },
    { code = "DM", name = "多米尼克 (Dominica)" },
    { code = "DO", name = "多米尼加共和国 (Dominican Republic)" },
    { code = "EC", name = "厄瓜多尔 (Ecuador)" },
    { code = "EG", name = "埃及 (Egypt)" },
    { code = "SV", name = "萨尔瓦多 (El Salvador)" },
    { code = "GQ", name = "赤道几内亚 (Equatorial Guinea)" },
    { code = "ER", name = "厄立特里亚 (Eritrea)" },
    { code = "EE", name = "爱沙尼亚 (Estonia)" },
    { code = "ET", name = "埃塞俄比亚 (Ethiopia)" },
    { code = "FK", name = "福克兰群岛（马尔维纳斯） (Falkland Islands (Malvinas))" },
    { code = "FO", name = "法罗群岛 (Faroe Islands)" },
    { code = "FJ", name = "斐济 (Fiji)" },
    { code = "FI", name = "芬兰 (Finland)" },
    { code = "FR", name = "法国 (France)" },
    { code = "GF", name = "法属圭亚那 (French Guiana)" },
    { code = "PF", name = "法属波利尼西亚 (French Polynesia)" },
    { code = "TF", name = "法属南部领地 (French Southern Territories)" },
    { code = "GA", name = "加蓬 (Gabon)" },
    { code = "GM", name = "冈比亚 (Gambia)" },
    { code = "GE", name = "格鲁吉亚 (Georgia)" },
    { code = "DE", name = "德国 (Germany)" },
    { code = "GH", name = "加纳 (Ghana)" },
    { code = "GI", name = "直布罗陀 (Gibraltar)" },
    { code = "GR", name = "希腊 (Greece)" },
    { code = "GL", name = "格陵兰 (Greenland)" },
    { code = "GD", name = "格林纳达 (Grenada)" },
    { code = "GP", name = "瓜德罗普 (Guadeloupe)" },
    { code = "GU", name = "关岛 (Guam)" },
    { code = "GT", name = "危地马拉 (Guatemala)" },
    { code = "GG", name = "根西岛 (Guernsey)" },
    { code = "GN", name = "几内亚 (Guinea)" },
    { code = "GW", name = "几内亚比绍 (Guinea-Bissau)" },
    { code = "GY", name = "圭亚那 (Guyana)" },
    { code = "HT", name = "海地 (Haiti)" },
    { code = "HM", name = "赫德岛和麦克唐纳群岛 (Heard Island and Mcdonald Islands)" },
    { code = "VA", name = "梵蒂冈 (Holy See (Vatican City State))" },
    { code = "HN", name = "洪都拉斯 (Honduras)" },
    { code = "HK", name = "香港 (Hong Kong)" },
    { code = "HU", name = "匈牙利 (Hungary)" },
    { code = "IS", name = "冰岛 (Iceland)" },
    { code = "IN", name = "印度 (India)" },
    { code = "ID", name = "印度尼西亚 (Indonesia)" },
    { code = "IR", name = "伊朗 (Iran, Islamic Republic Of)" },
    { code = "IQ", name = "伊拉克 (Iraq)" },
    { code = "IE", name = "爱尔兰 (Ireland)" },
    { code = "IM", name = "马恩岛 (Isle of Man)" },
    { code = "IL", name = "以色列 (Israel)" },
    { code = "IT", name = "意大利 (Italy)" },
    { code = "JM", name = "牙买加 (Jamaica)" },
    { code = "JP", name = "日本 (Japan)" },
    { code = "JE", name = "泽西岛 (Jersey)" },
    { code = "JO", name = "约旦 (Jordan)" },
    { code = "KZ", name = "哈萨克斯坦 (Kazakhstan)" },
    { code = "KE", name = "肯尼亚 (Kenya)" },
    { code = "KI", name = "基里巴斯 (Kiribati)" },
    { code = "KP", name = "朝鲜 (Korea, Democratic People's Republic of)" },
    { code = "KR", name = "韩国 (Korea, Republic of)" },
    { code = "KW", name = "科威特 (Kuwait)" },
    { code = "KG", name = "吉尔吉斯斯坦 (Kyrgyzstan)" },
    { code = "LA", name = "老挝 (Lao People's Democratic Republic)" },
    { code = "LV", name = "拉脱维亚 (Latvia)" },
    { code = "LB", name = "黎巴嫩 (Lebanon)" },
    { code = "LS", name = "莱索托 (Lesotho)" },
    { code = "LR", name = "利比里亚 (Liberia)" },
    { code = "LY", name = "利比亚 (Libyan Arab Jamahiriya)" },
    { code = "LI", name = "列支敦士登 (Liechtenstein)" },
    { code = "LT", name = "立陶宛 (Lithuania)" },
    { code = "LU", name = "卢森堡 (Luxembourg)" },
    { code = "MO", name = "澳门 (Macao)" },
    { code = "MK", name = "北马其顿 (Macedonia, The Former Yugoslav Republic of)" },
    { code = "MG", name = "马达加斯加 (Madagascar)" },
    { code = "MW", name = "马拉维 (Malawi)" },
    { code = "MY", name = "马来西亚 (Malaysia)" },
    { code = "MV", name = "马尔代夫 (Maldives)" },
    { code = "ML", name = "马里 (Mali)" },
    { code = "MT", name = "马耳他 (Malta)" },
    { code = "MH", name = "马绍尔群岛 (Marshall Islands)" },
    { code = "MQ", name = "马提尼克 (Martinique)" },
    { code = "MR", name = "毛里塔尼亚 (Mauritania)" },
    { code = "MU", name = "毛里求斯 (Mauritius)" },
    { code = "YT", name = "马约特 (Mayotte)" },
    { code = "MX", name = "墨西哥 (Mexico)" },
    { code = "FM", name = "密克罗尼西亚 (Micronesia, Federated States of)" },
    { code = "MD", name = "摩尔多瓦 (Moldova, Republic of)" },
    { code = "MC", name = "摩纳哥 (Monaco)" },
    { code = "MN", name = "蒙古 (Mongolia)" },
    { code = "MS", name = "蒙特塞拉特 (Montserrat)" },
    { code = "MA", name = "摩洛哥 (Morocco)" },
    { code = "MZ", name = "莫桑比克 (Mozambique)" },
    { code = "MM", name = "缅甸 (Myanmar)" },
    { code = "NA", name = "纳米比亚 (Namibia)" },
    { code = "NR", name = "瑙鲁 (Nauru)" },
    { code = "NP", name = "尼泊尔 (Nepal)" },
    { code = "NL", name = "荷兰 (Netherlands)" },
    { code = "AN", name = "荷属安的列斯 (Netherlands Antilles)" },
    { code = "NC", name = "新喀里多尼亚 (New Caledonia)" },
    { code = "NZ", name = "新西兰 (New Zealand)" },
    { code = "NI", name = "尼加拉瓜 (Nicaragua)" },
    { code = "NE", name = "尼日尔 (Niger)" },
    { code = "NG", name = "尼日利亚 (Nigeria)" },
    { code = "NU", name = "纽埃 (Niue)" },
    { code = "NF", name = "诺福克岛 (Norfolk Island)" },
    { code = "MP", name = "北马里亚纳群岛 (Northern Mariana Islands)" },
    { code = "NO", name = "挪威 (Norway)" },
    { code = "OM", name = "阿曼 (Oman)" },
    { code = "PK", name = "巴基斯坦 (Pakistan)" },
    { code = "PW", name = "帕劳 (Palau)" },
    { code = "PS", name = "巴勒斯坦 (Palestinian Territory, Occupied)" },
    { code = "PA", name = "巴拿马 (Panama)" },
    { code = "PG", name = "巴布亚新几内亚 (Papua New Guinea)" },
    { code = "PY", name = "巴拉圭 (Paraguay)" },
    { code = "PE", name = "秘鲁 (Peru)" },
    { code = "PH", name = "菲律宾 (Philippines)" },
    { code = "PN", name = "皮特凯恩 (Pitcairn)" },
    { code = "PL", name = "波兰 (Poland)" },
    { code = "PT", name = "葡萄牙 (Portugal)" },
    { code = "PR", name = "波多黎各 (Puerto Rico)" },
    { code = "QA", name = "卡塔尔 (Qatar)" },
    { code = "RE", name = "留尼汪 (Reunion)" },
    { code = "RO", name = "罗马尼亚 (Romania)" },
    { code = "RU", name = "俄罗斯 (Russian Federation)" },
    { code = "RW", name = "卢旺达 (Rwanda)" },
    { code = "SH", name = "圣赫勒拿 (Saint Helena)" },
    { code = "KN", name = "圣基茨和尼维斯 (Saint Kitts and Nevis)" },
    { code = "LC", name = "圣卢西亚 (Saint Lucia)" },
    { code = "PM", name = "圣皮埃尔和密克隆 (Saint Pierre and Miquelon)" },
    { code = "VC", name = "圣文森特和格林纳丁斯 (Saint Vincent and the Grenadines)" },
    { code = "WS", name = "萨摩亚 (Samoa)" },
    { code = "SM", name = "圣马力诺 (San Marino)" },
    { code = "ST", name = "圣多美和普林西比 (Sao Tome and Principe)" },
    { code = "SA", name = "沙特阿拉伯 (Saudi Arabia)" },
    { code = "SN", name = "塞内加尔 (Senegal)" },
    { code = "CS", name = "塞尔维亚和黑山 (Serbia and Montenegro)" },
    { code = "SC", name = "塞舌尔 (Seychelles)" },
    { code = "SL", name = "塞拉利昂 (Sierra Leone)" },
    { code = "SG", name = "新加坡 (Singapore)" },
    { code = "SK", name = "斯洛伐克 (Slovakia)" },
    { code = "SI", name = "斯洛文尼亚 (Slovenia)" },
    { code = "SB", name = "所罗门群岛 (Solomon Islands)" },
    { code = "SO", name = "索马里 (Somalia)" },
    { code = "ZA", name = "南非 (South Africa)" },
    { code = "GS", name = "南乔治亚和南桑威奇群岛 (South Georgia and the South Sandwich Islands)" },
    { code = "ES", name = "西班牙 (Spain)" },
    { code = "LK", name = "斯里兰卡 (Sri Lanka)" },
    { code = "SD", name = "苏丹 (Sudan)" },
    { code = "SR", name = "苏里南 (Suriname)" },
    { code = "SJ", name = "斯瓦尔巴和扬马延 (Svalbard and Jan Mayen)" },
    { code = "SZ", name = "斯威士兰 (Swaziland)" },
    { code = "SE", name = "瑞典 (Sweden)" },
    { code = "CH", name = "瑞士 (Switzerland)" },
    { code = "SY", name = "叙利亚 (Syrian Arab Republic)" },
    { code = "TW", name = "台湾 (Taiwan)" },
    { code = "TJ", name = "塔吉克斯坦 (Tajikistan)" },
    { code = "TZ", name = "坦桑尼亚 (Tanzania, United Republic of)" },
    { code = "TH", name = "泰国 (Thailand)" },
    { code = "TL", name = "东帝汶 (Timor-Leste)" },
    { code = "TG", name = "多哥 (Togo)" },
    { code = "TK", name = "托克劳 (Tokelau)" },
    { code = "TO", name = "汤加 (Tonga)" },
    { code = "TT", name = "特立尼达和多巴哥 (Trinidad and Tobago)" },
    { code = "TN", name = "突尼斯 (Tunisia)" },
    { code = "TR", name = "土耳其 (Turkey)" },
    { code = "TM", name = "土库曼斯坦 (Turkmenistan)" },
    { code = "TC", name = "特克斯和凯科斯群岛 (Turks and Caicos Islands)" },
    { code = "TV", name = "图瓦卢 (Tuvalu)" },
    { code = "UG", name = "乌干达 (Uganda)" },
    { code = "UA", name = "乌克兰 (Ukraine)" },
    { code = "AE", name = "阿拉伯联合酋长国 (United Arab Emirates)" },
    { code = "GB", name = "英国 (United Kingdom)" },
    { code = "US", name = "美国 (United States)" },
    { code = "UM", name = "美国本土外小岛屿 (United States Minor Outlying Islands)" },
    { code = "UY", name = "乌拉圭 (Uruguay)" },
    { code = "UZ", name = "乌兹别克斯坦 (Uzbekistan)" },
    { code = "VU", name = "瓦努阿图 (Vanuatu)" },
    { code = "VE", name = "委内瑞拉 (Venezuela)" },
    { code = "VN", name = "越南 (Viet Nam)" },
    { code = "VG", name = "英属维尔京群岛 (Virgin Islands, British)" },
    { code = "VI", name = "美属维尔京群岛 (Virgin Islands, U.S.)" },
    { code = "WF", name = "瓦利斯和富图纳 (Wallis and Futuna)" },
    { code = "EH", name = "西撒哈拉 (Western Sahara)" },
    { code = "YE", name = "也门 (Yemen)" },
    { code = "ZM", name = "赞比亚 (Zambia)" },
    { code = "ZW", name = "津巴布韦 (Zimbabwe)" },
}

-- Unicode转义解码辅助函数
local function decodeUnicodeEscape(str)
    if not str then return str end

    -- 将 \uXXXX 转换为 UTF-8
    local function unicodeToUtf8(code)
        code = tonumber(code, 16)
        if code < 0x80 then
            return string.char(code)
        elseif code < 0x800 then
            return string.char(
                0xC0 + math.floor(code / 0x40),
                0x80 + (code % 0x40)
            )
        elseif code < 0x10000 then
            return string.char(
                0xE0 + math.floor(code / 0x1000),
                0x80 + (math.floor(code / 0x40) % 0x40),
                0x80 + (code % 0x40)
            )
        end
        return "?"
    end

    -- 替换所有 \uXXXX 序列
    return str:gsub("\\u(%x%x%x%x)", unicodeToUtf8)
end

-- 简单的JSON解析函数
local function parseJSON(jsonString)
    local result = {}

    -- 提取 success 字段
    local success = string.match(jsonString, '"success"%s*:%s*([^,}]+)')
    if success then
        result.success = (success == "true")
    end

    -- 提取 results 数组中的第一个结果
    local resultsBlock = string.match(jsonString, '"results"%s*:%s*%[(.-)%]')
    if resultsBlock then
        result.results = {}

        -- 提取第一个结果对象
        local firstResult = string.match(resultsBlock, '{(.-)}')
        if firstResult then
            local item = {}

            -- 提取字段并解码Unicode
            local cn_name_raw = string.match(firstResult, '"cn_name"%s*:%s*"([^"]*)"')
            local en_name_raw = string.match(firstResult, '"en_name"%s*:%s*"([^"]*)"')
            local sci_name_raw = string.match(firstResult, '"scientific_name"%s*:%s*"([^"]*)"')
            local desc_raw = string.match(firstResult, '"description"%s*:%s*"([^"]*)"')

            item.cn_name = decodeUnicodeEscape(cn_name_raw)
            item.en_name = decodeUnicodeEscape(en_name_raw)
            item.scientific_name = decodeUnicodeEscape(sci_name_raw)
            item.description = decodeUnicodeEscape(desc_raw)

            local confStr = string.match(firstResult, '"confidence"%s*:%s*([%d%.]+)')
            item.confidence = confStr and tonumber(confStr) or 0

            table.insert(result.results, item)
        end
    end

    -- 提取 yolo_info (可能包含中文)
    local yolo_raw = string.match(jsonString, '"yolo_info"%s*:%s*"([^"]*)"')
    result.yolo_info = decodeUnicodeEscape(yolo_raw)

    -- 提取 gps_info
    local gpsBlock = string.match(jsonString, '"gps_info"%s*:%s*{(.-)}')
    if gpsBlock then
        result.gps_info = {}

        local lat = string.match(gpsBlock, '"latitude"%s*:%s*([%d%.%-]+)')
        local lon = string.match(gpsBlock, '"longitude"%s*:%s*([%d%.%-]+)')

        result.gps_info.latitude = lat and tonumber(lat) or nil
        result.gps_info.longitude = lon and tonumber(lon) or nil

        local region_raw = string.match(gpsBlock, '"region"%s*:%s*"([^"]*)"')
        local info_raw = string.match(gpsBlock, '"info"%s*:%s*"([^"]*)"')

        result.gps_info.region = decodeUnicodeEscape(region_raw)
        result.gps_info.info = decodeUnicodeEscape(info_raw)
    end

    -- 提取错误信息
    local error_raw = string.match(jsonString, '"error"%s*:%s*"([^"]*)"')
    result.error = decodeUnicodeEscape(error_raw)

    return result
end

-- 简单的JSON编码函数
local function encodeJSON(tbl)
    local parts = {}
    for k, v in pairs(tbl) do
        local key = '"' .. tostring(k) .. '"'
        local value
        if type(v) == "string" then
            value = '"' .. v:gsub('"', '\\"'):gsub('\\', '\\\\') .. '"'
        elseif type(v) == "boolean" then
            value = tostring(v)
        elseif type(v) == "number" then
            value = tostring(v)
        else
            value = '"' .. tostring(v) .. '"'
        end
        table.insert(parts, key .. ":" .. value)
    end
    return "{" .. table.concat(parts, ",") .. "}"
end

-- 识别单张照片并返回结果
local function recognizeSinglePhoto(photo, apiUrl, topK, useYolo, useGps)
    local LrHttp = import 'LrHttp'
    local LrFileUtils = import 'LrFileUtils'

    local photoPath = photo:getRawMetadata("path")
    local photoName = photo:getFormattedMetadata("fileName") or "Unknown"

    -- 检查文件是否存在
    if not LrFileUtils.exists(photoPath) then
        return {
            success = false,
            error = "文件不存在: " .. photoName,
            photoName = photoName
        }
    end

    -- 构建API请求
    local requestBody = encodeJSON({
        image_path = photoPath,
        use_yolo = useYolo,
        use_gps = useGps,
        top_k = topK
    })

    -- 调用API
    local response, headers = LrHttp.post(
        apiUrl .. "/recognize",
        requestBody,
        {
            { field = "Content-Type", value = "application/json" }
        }
    )

    if not response then
        return {
            success = false,
            error = "API调用失败",
            photoName = photoName
        }
    end

    -- 解析响应
    local result = parseJSON(response)
    result.photoName = photoName
    result.photo = photo

    return result
end

-- 保存识别结果到照片元数据
local function saveRecognitionResult(photo, species, enName, scientificName, description)
    local catalog = import('LrApplication').activeCatalog()

    -- 构建题注内容
    local caption = enName .. " (" .. scientificName .. ")"
    if description and description ~= "" then
        caption = caption .. "\n\n" .. description
    end

    catalog:withWriteAccessDo("保存鸟类识别结果", function()
        photo:setRawMetadata("title", species)
        photo:setRawMetadata("caption", caption)
    end)
end

-- UI配置
function exportServiceProvider.sectionsForTopOfDialog( f, propertyTable )
    local LrView = import 'LrView'
    local bind = LrView.bind

    return {
        {
            title = "🌐 SuperBirdID API 配置",

            synopsis = bind { key = 'apiUrl', object = propertyTable },

            f:row {
                spacing = f:control_spacing(),

                f:static_text {
                    title = "API 地址:",
                    width = LrView.share "label_width",
                },

                f:edit_field {
                    value = bind 'apiUrl',
                    width_in_chars = 30,
                    tooltip = "SuperBirdID API服务器地址，默认: http://127.0.0.1:5156",
                },
            },

            f:row {
                spacing = f:control_spacing(),

                f:static_text {
                    title = "返回结果数:",
                    width = LrView.share "label_width",
                },

                f:slider {
                    value = bind 'topK',
                    min = 1,
                    max = 10,
                    integral = true,
                    width = 200,
                },

                f:static_text {
                    title = bind 'topK',
                },
            },

            f:row {
                spacing = f:control_spacing(),

                f:checkbox {
                    title = "启用YOLO检测",
                    value = bind 'useYolo',
                    tooltip = "使用YOLO模型预检测鸟类位置",
                },
            },

            f:row {
                spacing = f:control_spacing(),

                f:checkbox {
                    title = "启用GPS定位",
                    value = bind 'useGps',
                    tooltip = "从EXIF读取GPS信息辅助识别",
                },
            },

            f:row {
                spacing = f:control_spacing(),

                f:checkbox {
                    title = "自动写入EXIF",
                    value = bind 'writeExif',
                    checked_value = true,
                    unchecked_value = false,
                    tooltip = "识别成功后自动写入鸟种名称到照片标题",
                },
            },

            f:row {
                spacing = f:control_spacing(),

                f:static_text {
                    title = "💡 提示: 请确保SuperBirdID API服务已启动",
                    text_color = import 'LrColor'( 0.5, 0.5, 0.5 ),
                },
            },
        },
    }
end

-- 主要处理函数
function exportServiceProvider.processRenderedPhotos( functionContext, exportContext )
    myLogger:info( "🦆 SuperBirdID 本地识别启动 - " .. VERSION )

    local exportSettings = exportContext.propertyTable
    local apiUrl = exportSettings.apiUrl or "http://127.0.0.1:5156"
    local topK = exportSettings.topK or 3
    local useYolo = exportSettings.useYolo
    if useYolo == nil then useYolo = true end
    local useGps = exportSettings.useGps
    if useGps == nil then useGps = true end
    local writeExif = exportSettings.writeExif
    if writeExif == nil then writeExif = true end

    -- 计算照片数量
    local nPhotos = exportContext.nPhotos or 1
    myLogger:info( "待处理照片数: " .. nPhotos )

    -- 限制只处理一张照片
    if nPhotos == 0 then
        LrDialogs.message("🦆 SuperBirdID 识别 - " .. VERSION,
            "❌ 没有选中要处理的照片\n\n请先选择一张照片再进行识别",
            "error")
        return
    elseif nPhotos > 1 then
        LrDialogs.message("🦆 SuperBirdID 识别 - " .. VERSION,
            "⚠️ 一次只能识别一张照片\n\n" ..
            "当前选中: " .. nPhotos .. " 张照片\n\n" ..
            "请重新选择，只选中一张照片后再次导出",
            "warning")
        return
    end

    -- 检查API服务是否可用
    myLogger:info( "检查API服务: " .. apiUrl .. "/health" )
    local healthCheck, headers = LrHttp.get(apiUrl .. "/health")

    if not healthCheck or string.find(healthCheck, '"status"%s*:%s*"ok"') == nil then
        LrDialogs.message("🦆 SuperBirdID 识别 - " .. VERSION,
            "❌ 无法连接到SuperBirdID API服务\n\n" ..
            "请确保:\n" ..
            "1. SuperBirdID API 已启动\n" ..
            "2. 服务地址正确: " .. apiUrl .. "\n" ..
            "3. 防火墙未阻止连接\n\n" ..
            "启动命令:\n" ..
            "python SuperBirdID_API.py --host 127.0.0.1 --port 5156",
            "error")
        return
    end

    myLogger:info( "✅ API服务正常，开始识别..." )

    -- 处理单张照片
    for i, rendition in exportContext:renditions() do
        local photo = rendition.photo
        local result = recognizeSinglePhoto(photo, apiUrl, topK, useYolo, useGps)

        if result.success and result.results and #result.results > 0 then
            local topBird = result.results[1]
            local species = topBird.cn_name or "未知"
            local enName = topBird.en_name or ""
            local scientificName = topBird.scientific_name or ""
            local confidence = topBird.confidence or 0

            myLogger:info( "识别成功: " .. species )

            -- 构建结果消息
            local message = "✅ 识别成功！\n\n" ..
                          "🎯 鸟种: " .. species .. "\n" ..
                          "🔤 英文: " .. enName .. "\n" ..
                          "📖 学名: " .. scientificName .. "\n" ..
                          "📊 置信度: " .. string.format("%.1f%%", confidence) .. "\n\n"

            if result.yolo_info then
                message = message .. "🤖 " .. result.yolo_info .. "\n"
            end

            if result.gps_info and result.gps_info.info then
                message = message .. "📍 " .. result.gps_info.info .. "\n"
                if result.gps_info.region then
                    message = message .. "🌍 地区: " .. result.gps_info.region .. "\n"
                end
            end

            -- 显示识别结果，询问是否保存
            local action = LrDialogs.confirm(
                "🦆 SuperBirdID 识别完成 - " .. VERSION,
                message .. "\n\n是否保存识别结果到照片元数据？",
                "确认保存",
                "取消"
            )

            if action == "ok" and writeExif then
                saveRecognitionResult(photo, species, enName, scientificName, topBird.description)
                myLogger:info( "✅ 用户确认保存，已写入元数据: " .. species )
            else
                myLogger:info( "❌ 用户取消保存" )
            end

        else
            local errorMsg = result.error or "未知错误"
            myLogger:info( "识别失败: " .. errorMsg )

            LrDialogs.message("🦆 SuperBirdID 识别失败 - " .. VERSION,
                "❌ 识别过程中出现错误:\n\n" .. errorMsg .. "\n\n" ..
                "请检查:\n" ..
                "• 照片中是否包含清晰的鸟类\n" ..
                "• 图片文件是否完整\n" ..
                "• SuperBirdID模型是否正确加载",
                "error")
        end
        break
    end

    myLogger:info( "🦆 SuperBirdID 识别处理完成" )
end

return exportServiceProvider
