import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { CardSceneNavigation } from "./CardSceneNavigation";
const scenes=[{id:"a",title:"Arrival"},{id:"b",title:"Bridge"},{id:"c",title:"Camp"}];
it("browses adjacent Contents order and disables both boundaries without looping",()=>{
 const select=vi.fn();const {rerender}=render(<CardSceneNavigation scenes={scenes} sceneId="a" onSelect={select} />);
 expect(screen.getByRole("button",{name:"Previous scene"})).toBeDisabled();
 fireEvent.click(screen.getByRole("button",{name:"Next scene"}));expect(select).toHaveBeenLastCalledWith("b");
 rerender(<CardSceneNavigation scenes={scenes} sceneId="c" onSelect={select} />);
 expect(screen.getByRole("button",{name:"Next scene"})).toBeDisabled();
 fireEvent.click(screen.getByRole("button",{name:"Previous scene"}));expect(select).toHaveBeenLastCalledWith("b");
 rerender(<CardSceneNavigation scenes={scenes} sceneId="missing" onSelect={select} />);
 expect(screen.getAllByRole("button").every(button=>button.hasAttribute("disabled"))).toBe(true);
});
