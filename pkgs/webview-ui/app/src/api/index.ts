import schema from "@/api/API.json" assert { type: "json" };
import { API, Error } from "@/api/API";
import { nanoid } from "nanoid";
import { Schema as Inventory } from "@/api/Inventory";

export type OperationNames = keyof API;
export type OperationArgs<T extends OperationNames> = API[T]["arguments"];
export type OperationResponse<T extends OperationNames> = API[T]["return"];

export type ApiEnvelope<T> =
  | {
      status: "success";
      data: T;
      op_key: string;
    }
  | Error;

export type Services = NonNullable<Inventory["services"]>;
export type ServiceNames = keyof Services;
export type ClanService<T extends ServiceNames> = Services[T];
export type ClanServiceInstance<T extends ServiceNames> = NonNullable<
  Services[T]
>[string];

export type SuccessQuery<T extends OperationNames> = Extract<
  OperationResponse<T>,
  { status: "success" }
>;
export type SuccessData<T extends OperationNames> = SuccessQuery<T>["data"];

export type ErrorQuery<T extends OperationNames> = Extract<
  OperationResponse<T>,
  { status: "error" }
>;
export type ErrorData<T extends OperationNames> = ErrorQuery<T>["errors"];

export type ClanOperations = {
  [K in OperationNames]: (str: string) => void;
};

export interface GtkResponse<T> {
  result: T;
  op_key: string;
}

const operations = schema.properties;
const operationNames = Object.keys(operations) as OperationNames[];

export const callApi = <K extends OperationNames>(
  method: K,
  args: OperationArgs<K>,
) => {
  console.log("Calling API", method, args);
  return (window as any)[method](args);
};

const deserialize =
  <T>(fn: (response: T) => void) =>
  (r: unknown) => {
    try {
      fn(r as T);
    } catch (e) {
      console.error("Error parsing JSON: ", e);
      window.localStorage.setItem("error", JSON.stringify(r));
      console.error(r);
      console.error("See localStorage 'error'");
      alert(`Error parsing JSON: ${e}`);
    }
  };
