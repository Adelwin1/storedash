export type AutosaveState =
  | "saving"
  | "saved"
  | "error";


type AutosaveEntry = {
  state: AutosaveState;
  error?: string;
};


const registry =
  new Map<
    string,
    AutosaveEntry
  >();


export function setAutosaveState(
  key: string,
  state: AutosaveState,
  error?: string,
) {
  registry.set(
    key,
    {
      state,
      error,
    }
  );
}


export async function waitForAutosaves(
  prefix: string,
  timeoutMs = 15000,
) {

  const started =
    Date.now();


  while (true) {

    const entries =
      Array.from(
        registry.entries()
      ).filter(
        ([key]) =>
          key.startsWith(
            prefix
          )
      );


    const saving =
      entries.some(
        ([, entry]) =>
          entry.state
          === "saving"
      );


    if (!saving) {

      const failures =
        entries.filter(
          ([, entry]) =>
            entry.state
            === "error"
        );


      if (
        failures.length
      ) {

        const details =
          failures.map(
            ([key, entry]) =>
              `${key}: ${
                entry.error
                || "save failed"
              }`
          );


        throw new Error(
          "Some automatic saves failed. "
          + details.join(
            " | "
          )
        );
      }


      return;
    }


    if (
      Date.now()
      - started
      > timeoutMs
    ) {

      throw new Error(
        "StoreDash is still saving changes. "
        + "Please try again in a moment."
      );
    }


    await new Promise(
      (resolve) =>
        setTimeout(
          resolve,
          50
        )
    );
  }
}
