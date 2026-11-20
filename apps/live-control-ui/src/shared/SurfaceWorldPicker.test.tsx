import {fireEvent,render,screen} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {listWorldContainers} from "../api/liveApi";
import {SurfaceWorldPicker} from "./SurfaceWorldPicker";
vi.mock("../api/liveApi",()=>({listWorldContainers:vi.fn()}));
afterEach(()=>vi.resetAllMocks());
it("offers actual World links without creating or selecting a session",async()=>{
 vi.mocked(listWorldContainers).mockResolvedValue({records:[{world_id:"elderwyld",name:"Elderwyld"}]} as never);
 render(<SurfaceWorldPicker surface="play"/>);
 expect(await screen.findByRole("link",{name:/Elderwyld/})).toHaveAttribute("href","/play?world=elderwyld&choose=1");
 expect(listWorldContainers).toHaveBeenCalledOnce();
});
it("offers a recoverable read error",async()=>{
 vi.mocked(listWorldContainers).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({records:[]} as never);
 render(<SurfaceWorldPicker surface="play"/>);fireEvent.click(await screen.findByRole("button",{name:"Retry World list"}));
 expect(await screen.findByRole("link",{name:"Create your World in Build"})).toHaveAttribute("href","/build");
 expect(listWorldContainers).toHaveBeenCalledTimes(2);
});

it("offers native Plan links without carrying an old document selector",async()=>{
 window.history.replaceState({},"","/plan?documentId=b7e0d9da-37ad-444a-9a62-25f7c61bb32d");
 vi.mocked(listWorldContainers).mockResolvedValue({records:[{world_id:"world with spaces",name:"Elderwyld"}]} as never);
 render(<SurfaceWorldPicker surface="plan"/>);
 expect(await screen.findByRole("link",{name:/Elderwyld/})).toHaveAttribute("href","/plan?world=world%20with%20spaces");
 expect(screen.queryByText("Open sessions →")).toBeNull();
 expect(listWorldContainers).toHaveBeenCalledOnce();
});

it.each([
 ["plan", "/plan?world=elderwyld"],
 ["play", "/play?world=elderwyld&choose=1"],
] as const)("selects a World in %s without replacing the document", async (surface, expected) => {
 window.history.replaceState({}, "", `/${surface}`);
 vi.mocked(listWorldContainers).mockResolvedValue({records:[{world_id:"elderwyld",name:"Elderwyld"}]} as never);
 render(<SurfaceWorldPicker surface={surface}/>);
 const link = await screen.findByRole("link", {name:/Elderwyld/});
 const onNavigate = vi.fn();
 window.addEventListener("popstate", onNavigate);
 try {
  document.addEventListener("click", event => event.preventDefault(), {once:true});
  fireEvent.click(link, {ctrlKey:true});
  expect(onNavigate).not.toHaveBeenCalled();
  fireEvent.click(link);
  expect(window.location.pathname + window.location.search).toBe(expected);
  expect(onNavigate).toHaveBeenCalledOnce();
 } finally {
  window.removeEventListener("popstate",onNavigate);
  window.history.replaceState({}, "", "/");
 }
});
