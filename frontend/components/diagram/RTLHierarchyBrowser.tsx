"use client";

import React, { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { ChevronRight, ChevronDown, FileCode, GitBranch, Eye, Search, Expand } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModuleNode {
  id: string;
  name: string;
  type: string;
  children: ModuleNode[];
  ports: Port[];
  signals: Signal[];
  instances: Instance[];
  metadata: Record<string, any>;
}

interface Port {
  name: string;
  direction: string;
  width: string;
}

interface Signal {
  name: string;
  type: string;
  width: string;
}

interface Instance {
  name: string;
  module: string;
}

interface DiagramData {
  mermaid: string;
  graphviz: string;
  hierarchy: ModuleNode[];
}

export function RTLHierarchyBrowser({ projectId, designId }: { projectId: string; designId: string }) {
  const [hierarchy, setHierarchy] = useState<ModuleNode[]>([]);
  const [diagram, setDiagram] = useState<DiagramData | null>(null);
  const [selectedNode, setSelectedNode] = useState<ModuleNode | null>(null);
  const [viewMode, setViewMode] = useState<"tree" | "diagram" | "split">("split");
  const [loading, setLoading] = useState(true);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState("");

  const fetchHierarchy = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/rtl/hierarchy/${designId}`);
      setHierarchy(response.data.modules);
      setDiagram(response.data.diagram);
    } catch (error) {
      console.error("Failed to fetch hierarchy:", error);
    } finally {
      setLoading(false);
    }
  }, [designId]);

  useEffect(() => {
    fetchHierarchy();
  }, [fetchHierarchy]);

  const toggleNode = (nodeId: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  const expandAll = () => {
    const allIds = new Set<string>();
    const collect = (nodes: ModuleNode[]) => {
      nodes.forEach(n => {
        allIds.add(n.id);
        collect(n.children);
      });
    };
    collect(hierarchy);
    setExpandedNodes(allIds);
  };

  const collapseAll = () => setExpandedNodes(new Set());

  const filteredHierarchy = useCallback(() => {
    if (!searchTerm) return hierarchy;
    const matches = new Set<string>();
    const check = (nodes: ModuleNode[]) => {
      nodes.forEach(n => {
        if (n.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            n.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
            n.ports.some(p => p.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
            n.signals.some(s => s.name.toLowerCase().includes(searchTerm.toLowerCase()))) {
          matches.add(n.id);
        }
        check(n.children);
      });
    };
    check(hierarchy);
    return hierarchy.filter(n => matches.has(n.id));
  }, [hierarchy, searchTerm]);

  const renderNode = (node: ModuleNode, depth: number = 0) => {
    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = node.children.length > 0;
    const isSelected = selectedNode?.id === node.id;

    return (
      <div key={node.id} style={{ marginLeft: depth * 20 }}>
        <div
          className={cn(
            "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors",
            isSelected && "bg-blue-900/30 border-l-2 border-blue-400",
            "hover:bg-gray-800/50"
          )}
          onClick={() => setSelectedNode(node)}
        >
          {hasChildren && (
            <button
              onClick={e => { e.stopPropagation(); toggleNode(node.id); }}
              className="p-1 text-gray-400 hover:text-white transition-colors"
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          )}
          <span className={cn("font-mono text-sm", isSelected ? "text-blue-300" : "text-gray-200")}>
            {node.name}
          </span>
          <span className="px-1.5 py-0.5 text-xs rounded bg-gray-700 text-gray-400">{node.type}</span>
          <span className="text-xs text-gray-500">({node.ports.length} ports, {node.signals.length} sigs)</span>
        </div>
        {isExpanded && hasChildren && (
          <div className="border-l border-gray-700 ml-4 mt-1">
            {node.children.map(renderNode).map((child, i) => <React.Fragment key={i}>{child}</React.Fragment>)}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center gap-3">
          <Search className="w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search modules, ports, signals..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white placeholder-gray-500 w-64 focus:outline-none focus:border-blue-500"
          />
          <div className="flex items-center gap-1 ml-4">
            <button
              onClick={expandAll}
              className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded text-gray-300 hover:text-white"
              title="Expand All"
            >
              <Expand className="w-3 h-3 inline mr-1" /> All
            </button>
            <button
              onClick={collapseAll}
              className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded text-gray-300 hover:text-white"
              title="Collapse All"
            >
              Collapse
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("tree")}
            className={cn("px-3 py-1.5 text-sm rounded transition-colors", viewMode === "tree" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700")}
          >
            Tree
          </button>
          <button
            onClick={() => setViewMode("diagram")}
            className={cn("px-3 py-1.5 text-sm rounded transition-colors", viewMode === "diagram" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700")}
          >
            Diagram
          </button>
          <button
            onClick={() => setViewMode("split")}
            className={cn("px-3 py-1.5 text-sm rounded transition-colors", viewMode === "split" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700")}
          >
            Split
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex">
        {viewMode !== "diagram" && (
          <div className={`flex-1 overflow-auto border-r border-gray-800 ${viewMode === "split" ? "max-w-md" : ""}`}>
            <div className="p-3">
              {filteredHierarchy().map(renderNode).map((child, i) => <React.Fragment key={i}>{child}</React.Fragment>)}
            </div>
          </div>
        )}

        {viewMode !== "tree" && (
          <div className={`flex-1 overflow-auto ${viewMode === "split" ? "min-w-0" : ""}`}>
            <div className="h-full p-3">
              {diagram?.mermaid && (
                <div className="h-full bg-gray-900 rounded-lg border border-gray-800 p-4 overflow-auto">
                  <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">{diagram.mermaid}</pre>
                </div>
              )}
              {!diagram?.mermaid && (
                <div className="flex items-center justify-center h-full text-gray-500">
                  No diagram available
                </div>
              )}
            </div>
          </div>
        )}

        {/* Details Panel */}
        {selectedNode && viewMode !== "diagram" && (
          <div className="w-80 border-l border-gray-800 bg-gray-900/50 overflow-auto">
            <div className="p-4 border-b border-gray-800">
              <h3 className="font-semibold text-white">{selectedNode.name}</h3>
              <span className="text-xs text-gray-400">{selectedNode.type}</span>
            </div>
            <div className="p-4 space-y-4">
              {/* Ports */}
              {selectedNode.ports.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-300 mb-2 flex items-center gap-2">
                    <GitBranch className="w-4 h-4" /> Ports ({selectedNode.ports.length})
                  </h4>
                  <div className="space-y-1 max-h-40 overflow-auto">
                    {selectedNode.ports.map(p => (
                      <div key={p.name} className="flex items-center gap-2 text-sm">
                        <span className={cn(
                          "px-1.5 py-0.5 rounded text-xs font-mono",
                          p.direction === "input" && "bg-blue-900/30 text-blue-300",
                          p.direction === "output" && "bg-green-900/30 text-green-300",
                          p.direction === "inout" && "bg-yellow-900/30 text-yellow-300"
                        )}>
                          {p.direction}
                        </span>
                        <span className="font-mono text-gray-200">{p.name}</span>
                        {p.width && <span className="text-gray-500">[{p.width}]</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Signals */}
              {selectedNode.signals.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-300 mb-2 flex items-center gap-2">
                    <FileCode className="w-4 h-4" /> Signals ({selectedNode.signals.length})
                  </h4>
                  <div className="space-y-1 max-h-40 overflow-auto">
                    {selectedNode.signals.map(s => (
                      <div key={s.name} className="flex items-center gap-2 text-sm">
                        <span className="px-1.5 py-0.5 rounded text-xs bg-purple-900/30 text-purple-300 font-mono">
                          {s.type}
                        </span>
                        <span className="font-mono text-gray-200">{s.name}</span>
                        {s.width && <span className="text-gray-500">[{s.width}]</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Instances */}
              {selectedNode.instances.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-300 mb-2 flex items-center gap-2">
                    <GitBranch className="w-4 h-4" /> Instances ({selectedNode.instances.length})
                  </h4>
                  <div className="space-y-1">
                    {selectedNode.instances.map(inst => (
                      <div key={inst.name} className="flex items-center gap-2 text-sm">
                        <span className="px-1.5 py-0.5 rounded text-xs bg-orange-900/30 text-orange-300">
                          {inst.module}
                        </span>
                        <span className="font-mono text-gray-200">{inst.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata */}
              {Object.keys(selectedNode.metadata).length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-300 mb-2">Metadata</h4>
                  <pre className="text-xs text-gray-400 bg-gray-800 p-2 rounded overflow-auto max-h-32">
                    {JSON.stringify(selectedNode.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default RTLHierarchyBrowser;