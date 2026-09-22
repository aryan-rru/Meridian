import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { RequirementsPicker } from "../../pages/Controls";
import { ScaleSelect } from "../../pages/Risks";

const requirements = [
  {
    id: "req-1",
    framework_id: "framework-1",
    framework_key: "iso27001",
    framework_name: "ISO 27001",
    framework_color: "#2563eb",
    code: "A.5.1",
    title: "Security policies",
    description: "",
    category: "Policies",
    sort_order: 1,
    mapped_control_count: 0,
    created_at: "",
    updated_at: "",
  },
  {
    id: "req-2",
    framework_id: "framework-2",
    framework_key: "soc2",
    framework_name: "SOC 2",
    framework_color: "#16a34a",
    code: "CC6.1",
    title: "Logical access",
    description: "",
    category: "Access",
    sort_order: 1,
    mapped_control_count: 0,
    created_at: "",
    updated_at: "",
  },
];

describe("core frontend components", () => {
  it("renders configured scale words and emits numeric changes", () => {
    const onChange = vi.fn();
    render(<ScaleSelect name="Likelihood" value={3} labels={{ "1": "Rare", "3": "Possible" }} onChange={onChange} />);

    expect(screen.getByRole("option", { name: "3 — Possible" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "2 — Level 2" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Likelihood" }), { target: { value: "4" } });
    expect(onChange).toHaveBeenCalledWith(4);
  });

  it("groups and searches requirements, then sets coverage level", () => {
    const onChange = vi.fn();
    render(<RequirementsPicker requirements={requirements} selected={{}} onChange={onChange} />);

    expect(screen.getByText("ISO 27001")).toBeInTheDocument();
    expect(screen.getByText("SOC 2")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Search requirements" }), { target: { value: "Logical" } });
    expect(screen.getByText("CC6.1")).toBeInTheDocument();
    expect(screen.queryByText("A.5.1")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onChange).toHaveBeenCalledWith("req-2", "full");
  });
});
