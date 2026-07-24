import type {
  StatblockDefinitionV1_Input,
  StatblockDefinitionV1_Output,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";

/** Compile-time structural compatibility: Output must be assignable to Input. */
type AssertOutputAssignableToInput =
  StatblockDefinitionV1_Output extends StatblockDefinitionV1_Input ? true : never;
const _outputAssignableToInput: AssertOutputAssignableToInput = true;
void _outputAssignableToInput;

export function definitionOutputToInput(
  output: StatblockDefinitionV1_Output,
): StatblockDefinitionV1_Input {
  return structuredClone(output);
}
