import { ObjectSheet } from "./ObjectSheet";
import {
  faction,
  location,
  relationshipHeavy,
  richNpc,
  sparseNpc,
} from "./fixtures/worldObjects";

export const SparseNpc = () => <ObjectSheet model={sparseNpc} />;
export const RichNpc = () => <ObjectSheet model={richNpc} />;
export const Location = () => <ObjectSheet model={location} />;
export const Faction = () => <ObjectSheet model={faction} />;
export const RelationshipHeavy = () => <ObjectSheet model={relationshipHeavy} />;
