export type FigmaFile = {
  document: Document;
  schemaVersion: number;
  components: Record<string, Component>;
};

export type Component = {
  key: string;
  name: string;
  remote: boolean;
  description: string;
};

export type FigmaNodeFile = {
  name: string;
  version: string;
  nodes: {
    [id: string]: FigmaFile;
  };
};

export type Node = Document | Instance | ComponentNode;

export type Document = {
  // Maybe: Split those types
  type: "DOCUMENT" | "CANVAS" | "FRAME" | "COMPONENT_SET";
  id: string;
  name: string;
  children?: Node[];
};

export type Instance = {
  type: "INSTANCE";
  id: string;
  name: string;
  children?: Node[];
  componentId: string;
};

export type ComponentNode = {
  type: "COMPONENT";
  id: string;
  name: string;
  children?: Node[];
};
