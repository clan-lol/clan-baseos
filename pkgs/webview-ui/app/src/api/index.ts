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

export const callApi = async <K extends OperationNames>(
  method: K,
  args: OperationArgs<K>,
): Promise<OperationResponse<K>> => {
  console.log("Calling API", method, args);
  const response = await (
    window as unknown as Record<
      OperationNames,
      (
        args: OperationArgs<OperationNames>,
      ) => Promise<OperationResponse<OperationNames>>
    >
  )[method](args);
  return response as OperationResponse<K>;
};
