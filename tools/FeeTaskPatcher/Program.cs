using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UAssetAPI;
using UAssetAPI.ExportTypes;
using UAssetAPI.UnrealTypes;
using UAssetAPI.Unversioned;

if (args.Length != 3)
{
    Console.Error.WriteLine("usage: FeeTaskPatcher <source.uasset> <mappings.usmap> <output.uasset>");
    return 2;
}

const string graphName = "ExecuteUbergraph_BTTask_Checkout-Fees";
const int graphPackageIndex = 12;
const int replaceStart = 14279;
const int replaceEnd = 14650;
const int cloneStart = 14650;
const int cloneEnd = 15227;
const int delta = (cloneEnd - cloneStart) - (replaceEnd - replaceStart);
const int expectedOldSize = 25314;
const int expectedNewSize = expectedOldSize + delta;

static string Hash(byte[] data) => Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
static string TypeName(JToken expression) =>
    ((string?)expression["$type"] ?? "").Split(',')[0].Split('.').Last();
static JObject ExportNamed(JArray exports, string name) => exports.Children<JObject>().Single(
    export => (string?)export["ObjectName"] == name);
static IEnumerable<JProperty> Properties(JToken token) => token is JContainer container
    ? container.DescendantsAndSelf().OfType<JProperty>()
    : token is JProperty property ? new[] { property } : Enumerable.Empty<JProperty>();
static IEnumerable<JProperty> FlowOffsets(JToken token) => Properties(token).Where(
    property => property.Name is "CodeOffset" or "PushingAddress" or "EndGotoOffset" or "NextOffset");

static void ReplacePath(JToken token, string oldValue, string newValue)
{
    var matches = Properties(token)
        .Where(property => property.Name == "Path" && (string?)property.Value.First == oldValue)
        .ToArray();
    if (matches.Length != 1)
        throw new InvalidDataException($"Expected one path {oldValue}, found {matches.Length}");
    matches[0].Value[0] = newValue;
}

var sourcePath = Path.GetFullPath(args[0]);
var mappingsPath = Path.GetFullPath(args[1]);
var outputPath = Path.GetFullPath(args[2]);
var sourceUasset = File.ReadAllBytes(sourcePath);
var sourceUexp = File.ReadAllBytes(Path.ChangeExtension(sourcePath, ".uexp"));
var mappings = File.ReadAllBytes(mappingsPath);
if (sourceUasset.Length != 34995
    || Hash(sourceUasset) != "269416f1f8b1312dd14d86fc03a018576ae375bb8fd252edb293b83ebb512a70"
    || sourceUexp.Length != 79230
    || Hash(sourceUexp) != "7149b15743357a65cce54278d3955dc86095ece434422123ad477a5d779e1e66"
    || mappings.Length != 1568015
    || Hash(mappings) != "b0a2faf0a86e3be731eb00f1b75fdccba26b8db78ecbd862a00e02802688bc23")
    throw new InvalidDataException("Unexpected source package or mappings");

var source = new UAsset(sourcePath, EngineVersion.VER_UE5_4, new Usmap(mappingsPath));
var root = JObject.Parse(source.SerializeJson(Formatting.None));
var exports = (JArray)root["Exports"]!;
var graph = ExportNamed(exports, graphName);
var bytecode = (JArray)graph["ScriptBytecode"]!;
if (exports.IndexOf(graph) + 1 != graphPackageIndex || bytecode.Count != 554
    || graph.Value<int>("ScriptBytecodeSize") != expectedOldSize)
    throw new InvalidDataException("Unexpected graph layout");

var original = (JArray)bytecode.DeepClone();
var replacement = new JArray(
    Enumerable.Range(221, 14).Select(index => original[index]!.DeepClone()));
var sourceGraph = (FunctionExport)source.Exports[graphPackageIndex - 1];
var originalReplacementSize = Enumerable.Range(214, 7)
    .Sum(index => (int)sourceGraph.ScriptBytecode[index].GetSize(source));
var cloneSize = Enumerable.Range(221, 14)
    .Sum(index => (int)sourceGraph.ScriptBytecode[index].GetSize(source));
if (originalReplacementSize != replaceEnd - replaceStart || cloneSize != cloneEnd - cloneStart)
    throw new InvalidDataException("Unexpected source branch sizes");

var graphRelocations = 0;
for (var index = 0; index < bytecode.Count; index++)
{
    foreach (var property in FlowOffsets(bytecode[index]!))
    {
        var value = property.Value.Value<int>();
        if (value < replaceEnd) continue;
        property.Value = value + delta;
        graphRelocations++;
    }
}
if (graphRelocations != 95)
    throw new InvalidDataException($"Unexpected graph relocation count: {graphRelocations}");

var wrapperRelocations = 0;
foreach (var export in exports.Children<JObject>().Where(export => !ReferenceEquals(export, graph)))
{
    if (export["ScriptBytecode"] is not JArray script) continue;
    foreach (var call in script.DescendantsAndSelf().OfType<JObject>().Where(item =>
        TypeName(item) == "EX_LocalFinalFunction" && (int?)item["StackNode"] == graphPackageIndex))
    {
        var parameters = (JArray?)call["Parameters"]
            ?? throw new InvalidDataException("Wrapper parameters missing");
        foreach (var entryPoint in parameters.Children<JObject>().Where(item =>
            TypeName(item) == "EX_IntConst"))
        {
            var value = entryPoint.Value<int>("Value");
            if (value < replaceEnd) continue;
            entryPoint["Value"] = value + delta;
            wrapperRelocations++;
        }
    }
}
if (wrapperRelocations != 22)
    throw new InvalidDataException($"Unexpected wrapper relocation count: {wrapperRelocations}");

ReplacePath(
    replacement,
    "DEV - Always ask has Broken Fees",
    "DEV - Always ask has Rewind Fees");
ReplacePath(
    replacement,
    "Broken_5_C1FEAF1341F90006475B01B94B5079AE",
    "Rewind_7_B80C9AFF4A03C0C5B9222088CEEB2842");
var enumAssignments = new[] { (JObject)replacement[7]!, (JObject)replacement[9]! };
if (enumAssignments.Any(expression => TypeName(expression) != "EX_Let"
    || (int?)expression["Expression"]?["Value"] != 5))
    throw new InvalidDataException("Unexpected Broken enum assignments");
foreach (var assignment in enumAssignments)
    assignment["Expression"]!["Value"] = 2;

foreach (var property in FlowOffsets(replacement))
{
    var value = property.Value.Value<int>();
    if (value < cloneStart || value > cloneEnd)
        throw new InvalidDataException($"Clone has external flow target {property.Name}={value}");
    property.Value = value - (cloneStart - replaceStart);
}

for (var index = 0; index < 7; index++) bytecode.RemoveAt(214);
for (var index = 0; index < replacement.Count; index++)
    bytecode.Insert(214 + index, replacement[index]!.DeepClone());
graph["ScriptBytecodeSize"] = expectedNewSize;

var patched = UAsset.DeserializeJson(root.ToString(Formatting.None));
patched.Mappings = source.Mappings;
var patchedGraph = (FunctionExport)patched.Exports[graphPackageIndex - 1];
var logicalSize = checked((int)patchedGraph.ScriptBytecode.Sum(
    expression => expression.GetSize(patched)));
if (logicalSize != expectedNewSize || patchedGraph.ScriptBytecode.Length != 561)
    throw new InvalidDataException(
        $"Unexpected patched graph: size={logicalSize} expressions={patchedGraph.ScriptBytecode.Length}");

Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
patched.Write(outputPath);
var outputUasset = File.ReadAllBytes(outputPath);
var outputUexp = File.ReadAllBytes(Path.ChangeExtension(outputPath, ".uexp"));
if (outputUasset.Length != 34995
    || Hash(outputUasset) != "760f08a168fc84883d91474e4e971583174e2c8816f379e99258a85af587ab0b"
    || outputUexp.Length != 79560
    || Hash(outputUexp) != "bfaa5fbea03bee43b1ba3836ed6a40cae180e59a8a1eb50863ae5733345cb6a6")
    throw new InvalidDataException("Structural output hash mismatch");

var verified = new UAsset(outputPath, EngineVersion.VER_UE5_4, new Usmap(mappingsPath));
var verifiedGraph = verified.Exports.OfType<FunctionExport>().Single(
    export => export.ObjectName.ToString() == graphName);
var verifiedSize = checked((int)verifiedGraph.ScriptBytecode.Sum(
    expression => expression.GetSize(verified)));
if (verifiedSize != expectedNewSize || verifiedGraph.ScriptBytecodeSize != expectedNewSize)
    throw new InvalidDataException("Round-trip logical size mismatch");

Console.WriteLine(
    $"BTTask rewind rows: logical={verifiedSize}, expressions={verifiedGraph.ScriptBytecode.Length}, "
    + $"uasset={Hash(outputUasset)}, uexp={Hash(outputUexp)}");
return 0;
