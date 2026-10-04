import Testing
@testable import Inference

@Test func stopMatcherHoldsBackPartialStop() {
    var m = StopMatcher(stops: ["END"])
    #expect(m.feed("hello E") == ("hello ", false))
    #expect(m.feed("N") == ("", false))
    #expect(m.feed("D tail") == ("", true))
}

@Test func stopMatcherReleasesFalseAlarm() {
    var m = StopMatcher(stops: ["END"])
    #expect(m.feed("an E") == ("an ", false))
    #expect(m.feed("xit") == ("Exit", false))
    #expect(m.finish() == "")
}

@Test func parsesQwen3JSONToolCall() {
    let text = "Let me check.\n<tool_call>\n{\"name\": \"get_weather\", \"arguments\": {\"city\": \"Oslo\"}}\n</tool_call>"
    let (content, calls) = ToolCallParser.parse(text)
    #expect(content == "Let me check.")
    #expect(calls == [ToolCall(name: "get_weather", arguments: "{\"city\":\"Oslo\"}")])
}

@Test func parsesQwen35XMLToolCall() {
    let text = """
        <tool_call>
        <function=get_weather>
        <parameter=city>
        Oslo
        </parameter>
        <parameter=days>
        3
        </parameter>
        </function>
        </tool_call>
        """
    let (content, calls) = ToolCallParser.parse(text)
    #expect(content == "")
    #expect(calls == [ToolCall(name: "get_weather", arguments: "{\"city\":\"Oslo\",\"days\":3}")])
}
