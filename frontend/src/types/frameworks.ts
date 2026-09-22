import type { Timestamped } from "./common";

export interface Framework extends Timestamped {
  key: string;
  name: string;
  version: string;
  description: string;
  color: string;
  sort_order: number;
  requirement_count: number;
}

export interface Requirement extends Timestamped {
  framework_id: string;
  framework_key: string;
  framework_name: string;
  framework_color: string;
  code: string;
  title: string;
  description: string;
  category: string;
  sort_order: number;
  mapped_control_count: number;
}
