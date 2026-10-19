import {fireEvent,render,screen} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {listWorldContainers} from "../api/liveApi";
import {PlayWorldPicker} from "./PlayWorldPicker";
vi.mock("../api/liveApi",()=>({listWorldContainers:vi.fn()}));
afterEach(()=>vi.resetAllMocks());
it("offers actual World links without creating or selecting a session",async()=>{
 vi.mocked(listWorldContainers).mockResolvedValue({records:[{world_id:"elderwyld",name:"Elderwyld"}]} as never);
 render(<PlayWorldPicker/>);
 expect(await screen.findByRole("link",{name:/Elderwyld/})).toHaveAttribute("href","/play?world=elderwyld&choose=1");
 expect(listWorldContainers).toHaveBeenCalledOnce();
});
it("offers a recoverable read error",async()=>{
 vi.mocked(listWorldContainers).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({records:[]} as never);
 render(<PlayWorldPicker/>);fireEvent.click(await screen.findByRole("button",{name:"Retry World list"}));
 expect(await screen.findByRole("link",{name:"Create your World in Build"})).toHaveAttribute("href","/build");
 expect(listWorldContainers).toHaveBeenCalledTimes(2);
});
