"use client";

import React, { useRef, useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import { cn } from "@/lib/utils";

// Register SystemVerilog language
if (typeof window !== "undefined") {
  monaco.languages.register({ id: "systemverilog" });
  monaco.languages.setMonarchTokensProvider("systemverilog", {
    keywords: [
      "module", "endmodule", "interface", "endinterface", "package", "endpackage",
      "program", "endprogram", "class", "endclass", "function", "endfunction",
      "task", "endtask", "initial", "always", "always_comb", "always_ff", "always_latch",
      "if", "else", "case", "casez", "casex", "endcase", "default",
      "for", "while", "repeat", "foreach", "forever", "break", "continue",
      "return", "begin", "end", "fork", "join", "join_any", "join_none",
      "wait", "wait_until", "expect", "assume", "assert", "cover",
      "property", "endproperty", "sequence", "endsequence",
      "input", "output", "inout", "ref", "const",
      "logic", "bit", "byte", "shortint", "int", "longint",
      "integer", "time", "real", "shortreal", "realtime",
      "string", "chandle", "event", "void",
      "signed", "unsigned", "rand", "randc",
      "localparam", "parameter", "typedef", "enum", "struct", "union",
      "virtual", "protected", "local", "static", "automatic",
      "import", "export", "package", "include",
      "posedge", "negedge", "edge", "disable", "deassign", "force", "release",
      "assign", "deassign", "bind", "config", "design", "cell", "instance",
      "default", "case", "endcase", "casez", "casex",
      "generate", "endgenerate", "if", "else", "elsif",
    ],
    operators: [
      "=", ">", "<", "!", "~", "?", ":",
      "==", "<=", ">=", "!=", "&&", "||", "++", "--",
      "+", "-", "*", "/", "%", "&", "|", "^", "~", "<<", ">>",
      "===", "!==", "~&", "~|", "~^", "^~",
      "->", "<->", "##", "##[", "=:", "=~", "=~>",
    ],
    symbols: /[=><!~?:&|+\-*/%^]+/,
    escapes: /\\(?:[abfnrtv\\"']|x[0-9A-Fa-f]{1,4}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})/,
    tokenizer: {
      root: [
        [/[a-zA-Z_$][\w$]*/, { cases: { "@keywords": "keyword", "@default": "identifier" } }],
        [/[0-9]+'[sbdo][0-9a-zA-Z_]+/, "number"],
        [/[0-9]+\.[0-9]+([eE][\-+]?[0-9]+)?/, "number.float"],
        [/[0-9]+/, "number"],
        [/"([^"\\]|\\.)*$/, "string.invalid"],
        [/"/, "string", "@string"],
        [/`[a-zA-Z_][\w$]*/, "metatag"],
        [/@symbols/, { cases: { "@operators": "operator", "@default": "" } }],
        [/[;,.]/, "delimiter"],
        [/[{}[\]]/, "@brackets"],
        [/\/\*/, "comment", "@comment"],
        [/\/\/.*$/, "comment"],
      ],
      string: [
        [/[^\\"]+/, "string"],
        [/@escapes/, "string.escape"],
        [/\\./, "string.escape.invalid"],
        [/"/, "string", "@pop"],
      ],
      comment: [
        [/[^\/*]+/, "comment"],
        [/\*\//, "comment", "@pop"],
        [/[\/*]/, "comment"],
      ],
    },
  });

  // Define SystemVerilog language configuration
  monaco.languages.setLanguageConfiguration("systemverilog", {
    comments: {
      lineComment: "//",
      blockComment: ["/*", "*/"],
    },
    brackets: [
      ["{", "}"],
      ["[", "]"],
      ["(", ")"],
      ["begin", "end"],
      ["module", "endmodule"],
      ["interface", "endinterface"],
      ["function", "endfunction"],
      ["task", "endtask"],
      ["class", "endclass"],
      ["case", "endcase"],
      ["generate", "endgenerate"],
    ],
    autoClosingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
      { open: "`", close: "`" },
      { open: "begin", close: "end" },
      { open: "module", close: "endmodule" },
      { open: "function", close: "endfunction" },
      { open: "task", close: "endtask" },
      { open: "case", close: "endcase" },
    ],
    surroundingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
    ],
    folding: {
      markers: {
        start: new RegExp("^\\s*//\\s*#?region\\b"),
        end: new RegExp("^\\s*//\\s*#?endregion\\b"),
      },
    },
  });
}

interface MonacoEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  theme?: string;
  readOnly?: boolean;
  height?: string;
  width?: string;
  className?: string;
  minimap?: boolean;
  lineNumbers?: "on" | "off" | "relative" | "interval";
  tabSize?: number;
  fontSize?: number;
  wordWrap?: "off" | "on" | "wordWrapColumn" | "bounded";
  autoIndent?: "none" | "keep" | "brackets" | "advanced" | "full";
  formatOnPaste?: boolean;
  formatOnType?: boolean;
  folding?: boolean;
  renderLineHighlight?: "none" | "gutter" | "line" | "all";
  scrollBeyondLastLine?: boolean;
  smoothScrolling?: boolean;
  cursorBlinking?: "blink" | "smooth" | "phase" | "expand" | "solid";
  cursorSmoothCaretAnimation?: "on" | "off";
  experimentalAsyncScroll?: boolean;
}

export function MonacoEditor({
  value,
  onChange,
  language = "systemverilog",
  theme = "vs-dark",
  readOnly = false,
  height = "400px",
  width = "100%",
  className,
  minimap = true,
  lineNumbers = "on",
  tabSize = 2,
  fontSize = 13,
  wordWrap = "on",
  autoIndent = "full",
  formatOnPaste = true,
  formatOnType = true,
  folding = true,
  renderLineHighlight = "line",
  scrollBeyondLastLine = false,
  smoothScrolling = true,
  cursorBlinking = "smooth",
  cursorSmoothCaretAnimation = "on",
}: MonacoEditorProps) {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleEditorDidMount = (editor: monaco.editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
    
    // Configure editor options
    editor.updateOptions({
      minimap: { enabled: minimap },
      lineNumbers,
      tabSize,
      fontSize,
      wordWrap,
      autoIndent,
      formatOnPaste,
      formatOnType,
      folding,
      renderLineHighlight,
      scrollBeyondLastLine,
      smoothScrolling,
      cursorBlinking,
      cursorSmoothCaretAnimation,
      readOnly,
      scrollbar: {
        vertical: "auto",
        horizontal: "auto",
        useShadows: true,
        verticalHasArrows: false,
        horizontalHasArrows: false,
      },
      find: {
        addExtraSpaceOnTop: true,
        seedSearchStringFromSelection: "always",
        autoFindInSelection: "never",
      },
      bracketPairColorization: { enabled: true },
      guides: {
        bracketPairs: true,
        indentation: true,
      },
      renderWhitespace: "selection",
      renderControlCharacters: true,
      renderIndentGuides: true,
      highlightActiveIndentGuide: true,
    });
  };

  const handleEditorWillMount = (monacoInstance: typeof monaco) => {
    // Register custom language features
    monacoInstance.languages.registerCompletionItemProvider("systemverilog", {
      provideCompletionItems: (model, position) => {
        const textUntilPosition = model.getValueInRange({
          startLineNumber: position.lineNumber,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column,
        });

        const suggestions = [
          {
            label: "module",
            kind: monacoInstance.languages.CompletionItemKind.Snippet,
            insertText: "module ${1:name} (${2:ports});\n\n  ${3}\n\nendmodule",
            insertTextRules: monacoInstance.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Module declaration",
          },
          {
            label: "always_ff",
            kind: monacoInstance.languages.CompletionItemKind.Snippet,
            insertText: "always_ff @(posedge ${1:clk} or negedge ${2:rst_n}) begin\n  if (!${2:rst_n}) begin\n    ${3}\n  end else begin\n    ${4}\n  end\nend",
            insertTextRules: monacoInstance.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Sequential always block with async reset",
          },
          {
            label: "always_comb",
            kind: monacoInstance.languages.CompletionItemKind.Snippet,
            insertText: "always_comb begin\n  ${1}\nend",
            insertTextRules: monacoInstance.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Combinational always block",
          },
          {
            label: "case",
            kind: monacoInstance.languages.CompletionItemKind.Snippet,
            insertText: "case (${1:expr})\n  ${2:val}: begin\n    ${3}\n  end\n  default: begin\n    ${4}\n  end\nendcase",
            insertTextRules: monacoInstance.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Case statement",
          },
          {
            label: "assert",
            kind: monacoInstance.languages.CompletionItemKind.Snippet,
            insertText: "property ${1:name}_p;\n  @(posedge ${2:clk}) disable iff (${3:rst})\n  ${4:condition} |-> ${5:consequence};\nendproperty\n${1:name}_a: assert property (${1:name}_p);",
            insertTextRules: monacoInstance.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Assertion property",
          },
          {
            label: "cover",
            kind: monacoInstance.languages.CompletionItemKind.Snippet,
            insertText: "property ${1:name}_p;\n  @(posedge ${2:clk}) disable iff (${3:rst})\n  ${4:condition};\nendproperty\n${1:name}_c: cover property (${1:name}_p);",
            insertTextRules: monacoInstance.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Cover property",
          },
          {
            label: "typedef enum",
            kind: monacoInstance.languages.CompletionItemKind.Snippet,
            insertText: "typedef enum logic [${1:1}:0] {\n  ${2:STATE_0} = ${3:2'b00},\n  ${4:STATE_1} = ${5:2'b01},\n  ${6:STATE_2} = ${7:2'b10},\n  ${8:STATE_3} = ${9:2'b11}\n} ${10:state_t};",
            insertTextRules: monacoInstance.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Enum type declaration",
          },
        ];

        return { suggestions };
      },
    });

    // Register hover provider
    monacoInstance.languages.registerHoverProvider("systemverilog", {
      provideHover: (model, position) => {
        const word = model.getWordAtPosition(position);
        if (!word) return null;

        const hovers: Record<string, string> = {
          "module": "Module declaration - defines a hardware block",
          "always_ff": "Sequential logic block - triggers on clock edges",
          "always_comb": "Combinational logic block - triggers on any input change",
          "always_latch": "Latch inference block - triggers on level-sensitive condition",
          "case": "Case statement - multi-way branch",
          "assert": "Immediate assertion - checks condition at current time",
          "property": "Property declaration - for assertions and coverage",
          "cover": "Cover property - tracks coverage of a condition",
          "typedef": "Type definition - creates a new type alias",
          "enum": "Enumeration type - defines a set of named values",
          "parameter": "Module parameter - compile-time constant",
          "localparam": "Local parameter - compile-time constant, not overridable",
          "rand": "Random variable - for constrained-random verification",
          "randc": "Cyclic random variable - cycles through all values",
          "constraint": "Constraint block - constrains random variables",
          "uvm_sequence_item": "UVM sequence item - transaction representation",
          "uvm_sequence": "UVM sequence - generates stimulus",
          "uvm_driver": "UVM driver - drives signals to DUT",
          "uvm_monitor": "UVM monitor - observes DUT signals",
          "uvm_scoreboard": "UVM scoreboard - checks DUT behavior",
          "uvm_agent": "UVM agent - encapsulates driver, monitor, sequencer",
          "uvm_env": "UVM environment - contains agents and scoreboards",
          "uvm_test": "UVM test - top-level test scenario",
        };

        if (hovers[word.word]) {
          return {
            range: new monacoInstance.Range(
              position.lineNumber,
              word.startColumn,
              position.lineNumber,
              word.endColumn
            ),
            contents: [{ value: hovers[word.word] }],
          };
        }

        return null;
      },
    });
  };

  if (!mounted) {
    return (
      <div
        className={cn("border border-gray-700 rounded-lg bg-gray-950", className)}
        style={{ height, width }}
      >
        <div className="p-4 text-gray-500 text-center">
          Loading editor...
        </div>
      </div>
    );
  }

  return (
    <Editor
      height={height}
      width={width}
      defaultLanguage={language}
      theme={theme}
      value={value}
      onChange={(val) => val && onChange(val)}
      onMount={handleEditorDidMount}
      onBeforeMount={handleEditorWillMount}
      options={{
        minimap: { enabled: minimap },
        lineNumbers,
        tabSize,
        fontSize,
        wordWrap,
        autoIndent,
        formatOnPaste,
        formatOnType,
        folding,
        renderLineHighlight,
        scrollBeyondLastLine,
        smoothScrolling,
        cursorBlinking,
        cursorSmoothCaretAnimation,
        readOnly,
        scrollbar: {
          vertical: "auto",
          horizontal: "auto",
          useShadows: true,
          verticalHasArrows: false,
          horizontalHasArrows: false,
        },
        find: {
          addExtraSpaceOnTop: true,
          seedSearchStringFromSelection: "always",
          autoFindInSelection: "never",
        },
        bracketPairColorization: { enabled: true },
        guides: {
          bracketPairs: true,
          indentation: true,
        },
        renderWhitespace: "selection",
        renderControlCharacters: true,
        renderIndentGuides: true,
        highlightActiveIndentGuide: true,
      }}
      className={cn("border border-gray-700 rounded-lg bg-gray-950", className)}
    />
  );
}

export default MonacoEditor;