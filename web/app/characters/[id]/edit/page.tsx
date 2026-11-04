"use client";
import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  Avatar,
  Character,
  Portrait,
  Profile,
  Proposal,
  Revision,
} from "@/components/api";

const sections = [
  {
    title: "Basic Information",
    subtitle: "Every story starts somewhere",
    fields: [
      ["name", "Name"],
      ["short_description", "Short description"],
      ["backstory", "Backstory"],
    ],
  },
  {
    title: "Appearance",
    subtitle: "Picture your character",
    fields: [
      ["appearance.age_description", "Age description"],
      ["appearance.hair", "Hair"],
      ["appearance.eyes", "Eyes"],
      ["appearance.clothing", "Clothing"],
      ["appearance.other_details", "Other details"],
    ],
  },
  {
    title: "Personality",
    subtitle: "Give your character an inner world",
    fields: [
      ["personality.core_traits", "Core traits"],
      ["personality.values", "Values"],
      ["personality.motivations", "Motivations"],
      ["personality.behavioral_patterns", "Behavioral patterns"],
    ],
  },
  {
    title: "Speech and Interaction",
    subtitle: "A voice of their own",
    fields: [
      ["speech_style.tone", "Tone"],
      ["speech_style.vocabulary", "Vocabulary"],
      ["speech_style.speaking_habits", "Speaking habits"],
      ["interaction_preferences.conversation_style", "Conversation style"],
      ["interaction_preferences.relationship_context", "Relationship context"],
    ],
  },
];
const labels = Object.fromEntries(
  sections.flatMap((s) => s.fields).map(([key, label]) => [key, label]),
);
function valueAt(profile: Profile, path: string): string | string[] {
  return path
    .split(".")
    .reduce(
      (obj, key) => (obj as Record<string, unknown>)[key],
      profile as unknown,
    ) as string | string[];
}
function display(value: string | string[]) {
  return Array.isArray(value)
    ? value.join(", ") || "(empty)"
    : value || "(empty)";
}

export default function Editor({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const base = `/characters/${id}`;
  const [character, setCharacter] = useState<Character | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [images, setImages] = useState<Portrait[]>([]);
  const [versions, setVersions] = useState<Revision[]>([]);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [instruction, setInstruction] = useState("");
  const [imageInstruction, setImageInstruction] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const guard = useRef(false);
  const load = useCallback(async () => {
    const [c, i, v] = await Promise.all([
      api<Character>(base),
      api<Portrait[]>(`${base}/images`),
      api<Revision[]>(`${base}/versions`),
    ]);
    setCharacter(c);
    setProfile(structuredClone(c.profile));
    setImages(i);
    setVersions(v);
  }, [base]);
  useEffect(() => {
    void load().catch((e) => setError(e.message));
  }, [load]);
  const dirty =
    character && profile
      ? JSON.stringify(character.profile) !== JSON.stringify(profile)
      : false;
  useEffect(() => {
    function warn(e: BeforeUnloadEvent) {
      if (dirty) e.preventDefault();
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function setField(path: string, value: string | string[]) {
    setProfile((old) => {
      if (!old) return old;
      const copy = structuredClone(old);
      const parts = path.split(".");
      const parent = (parts.length === 1
        ? copy
        : copy[parts[0] as keyof Profile]) as unknown as Record<
        string,
        unknown
      >;
      parent[parts.at(-1)!] = value;
      return copy;
    });
    setProposal(null);
    setNotice("");
  }
  async function action(label: string, fn: () => Promise<void>) {
    if (guard.current) return;
    guard.current = true;
    setBusy(label);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      guard.current = false;
      setBusy("");
    }
  }
  function update(c: Character) {
    setCharacter(c);
    setProfile(structuredClone(c.profile));
    setProposal(null);
  }
  if (!character || !profile)
    return (
      <main className="container">
        {error ? (
          <div className="error" role="alert">
            {error}
            <button onClick={() => load().catch((e) => setError(e.message))}>
              Retry
            </button>
          </div>
        ) : (
          <p role="status">Opening the character studio…</p>
        )}
      </main>
    );
  return (
    <main className="container editor-container">
      <Link
        className="back-link"
        href="/characters"
        onClick={(e) => {
          if (dirty && !confirm("You have unsaved changes. Leave this page?"))
            e.preventDefault();
        }}
      >
        ← My Characters
      </Link>
      <section className="page-intro compact">
        <div>
          <p className="eyebrow">CHARACTER STUDIO</p>
          <h1>Shape {character.profile.name}</h1>
          <p className="muted">
            Every detail brings them closer to your imagination.
          </p>
        </div>
        <Link
          className="button"
          href={`${base}/chat`}
          onClick={(e) => {
            if (
              dirty &&
              !confirm(
                "Your changes are not saved. Start chatting with the saved profile?",
              )
            )
              e.preventDefault();
          }}
        >
          Start chat ↗
        </Link>
      </section>
      <div className="status-bar" aria-live="polite">
        <span className={dirty ? "unsaved" : "saved"}>
          {dirty
            ? "● Unsaved changes"
            : `✓ Saved · Profile v${character.profile_version}`}
        </span>
        {notice && <span>{notice}</span>}
        {busy && <span role="status">{busy}…</span>}
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <div className="editor-layout">
        <aside className="portrait-column">
          <section className="panel portrait-panel">
            <Avatar character={character} large />
            <h2>{character.profile.name}</h2>
            <p className="muted">
              Portraits are optional. You can start chatting right away.
            </p>
            <label htmlFor="visual-style">Visual style</label>
            <select
              id="visual-style"
              value={profile.visual_style}
              disabled={!!busy}
              onChange={(e) => setField("visual_style", e.target.value)}
            >
              {[
                ["Anime", "Anime"],
                ["Cartoon", "Cartoon"],
                ["Semi-realistic", "Semi-realistic"],
                ["Realistic", "Realistic"],
              ].map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
            <button
              className="button full"
              disabled={!!busy || !!dirty}
              onClick={() =>
                action("Generating a portrait, please wait", async () => {
                  await api(`${base}/images/generate`, {
                    expected_image_id: character.current_image_id,
                  });
                  setImages(await api(`${base}/images`));
                  setNotice(
                    "Your portrait is ready. Preview it below and choose whether to use it.",
                  );
                })
              }
            >
              ✧ Generate portrait
            </button>
            {dirty && (
              <small className="muted">
                Save your profile before generating a portrait or requesting AI
                refinement.
              </small>
            )}
            {character.current_image_id && (
              <>
                <label htmlFor="image-edit">Edit current portrait</label>
                <textarea
                  id="image-edit"
                  rows={3}
                  maxLength={2000}
                  value={imageInstruction}
                  disabled={!!busy}
                  onChange={(e) => setImageInstruction(e.target.value)}
                  placeholder="For example: Make the hair dark blue and keep everything else the same"
                />
                <small className="muted">
                  AI edits may change other details. The original is kept;
                  preview the result before selecting it.
                </small>
                <button
                  className="button full"
                  disabled={!!busy || !imageInstruction.trim() || !!dirty}
                  onClick={() =>
                    action("Editing your portrait, please wait", async () => {
                      await api(`${base}/images/edit`, {
                        instruction: imageInstruction,
                        expected_image_id: character.current_image_id,
                      });
                      setImages(await api(`${base}/images`));
                      setNotice(
                        "Your edit is ready. Compare the versions and select your favorite.",
                      );
                    })
                  }
                >
                  Edit portrait
                </button>
              </>
            )}
          </section>
          {images.length > 0 && (
            <section className="panel">
              <h3>Portrait version</h3>
              <p className="muted small">
                Selecting a portrait does not change the character profile.
              </p>
              <div className="image-history">
                {images.map((image) => (
                  <div
                    key={image.id}
                    className={`image-version ${image.id === character.current_image_id ? "selected" : ""}`}
                  >
                    <img
                      src={image.url}
                      alt={`Portrait version ${image.version}`}
                    />
                    <small>
                      v{image.version}
                      {image.parent_image_id ? " · Edit" : " · Generated"}
                    </small>
                    {image.id === character.current_image_id ? (
                      <span className="saved">In use</span>
                    ) : (
                      <>
                        <button
                          disabled={!!busy}
                          onClick={() =>
                            action("Selecting portrait", async () => {
                              const c = await api<Character>(
                                `${base}/images/${image.id}/select`,
                                {},
                              );
                              // Keep the profile version tied to the form that was loaded.
                              // Selecting an image must not make stale form edits look current.
                              setCharacter((old) =>
                                old
                                  ? {
                                      ...old,
                                      current_image_id: c.current_image_id,
                                    }
                                  : c,
                              );
                              setNotice("Portrait saved.");
                            })
                          }
                        >
                          Use this version
                        </button>
                        <button
                          className="text-button danger"
                          disabled={!!busy}
                          onClick={() =>
                            action("Removing image", async () => {
                              await api(
                                `${base}/images/${image.id}`,
                                undefined,
                                "DELETE",
                              );
                              setImages(await api(`${base}/images`));
                            })
                          }
                        >
                          Discard
                        </button>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
          <section className="panel">
            <h3>Original inspiration</h3>
            <p className="original-description">
              {character.original_description}
            </p>
            <p className="muted small">
              Compare AI suggestions with your original request. Unspecified
              details may be creative additions, and every field is editable.
            </p>
          </section>
        </aside>
        <div className="profile-column">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void action("Saving profile", async () => {
                const c = await api<Character>(
                  base,
                  { profile, expected_version: character.profile_version },
                  "PATCH",
                );
                update(c);
                setVersions(await api(`${base}/versions`));
                setNotice(
                  "Changes saved. Future replies will use the updated profile.",
                );
              });
            }}
          >
            {sections.map((section, index) => (
              <section className="panel profile-section" key={section.title}>
                <div className="section-heading">
                  <span className="section-number">0{index + 1}</span>
                  <div>
                    <h2>{section.title}</h2>
                    <p className="muted small">{section.subtitle}</p>
                  </div>
                </div>
                <div className="field-grid">
                  {section.fields.map(([path, label]) => {
                    const value = valueAt(profile, path);
                    const list = Array.isArray(value);
                    const multiline = list || path === "backstory";
                    return (
                      <label
                        className={
                          multiline || path === "short_description"
                            ? "wide"
                            : ""
                        }
                        key={path}
                      >
                        {label}
                        {list && (
                          <span className="field-hint">
                            {" "}
                            · One item per line
                          </span>
                        )}
                        {multiline ? (
                          <textarea
                            disabled={!!busy}
                            rows={path === "backstory" ? 4 : 3}
                            maxLength={path === "backstory" ? 4000 : 15000}
                            value={list ? value.join("\n") : value}
                            onChange={(e) =>
                              setField(
                                path,
                                list
                                  ? e.target.value.split("\n")
                                  : e.target.value,
                              )
                            }
                          />
                        ) : (
                          <input
                            disabled={!!busy}
                            required={path === "name"}
                            maxLength={path === "name" ? 100 : 500}
                            value={value as string}
                            onChange={(e) => setField(path, e.target.value)}
                          />
                        )}
                      </label>
                    );
                  })}
                </div>
              </section>
            ))}
            <div className="save-strip">
              <p>
                {dirty
                  ? "Saved changes apply to future conversations."
                  : "Your profile and conversations are saved independently. Come back anytime."}
              </p>
              <button
                className="button primary"
                disabled={!!busy || !dirty || !profile.name.trim()}
              >
                Save changes
              </button>
            </div>
          </form>
          <section className="panel refine-panel">
            <p className="eyebrow">SHAPE, DON’T RESTART</p>
            <h2>Refine them in a few words.</h2>
            <p className="muted">
              Review the proposed changes before accepting them. Your
              conversations and portrait are preserved.
            </p>
            <label htmlFor="refinement">What would you like to change?</label>
            <textarea
              id="refinement"
              rows={3}
              maxLength={2000}
              disabled={!!busy}
              value={instruction}
              onChange={(e) => {
                setInstruction(e.target.value);
                setProposal(null);
              }}
              placeholder="Make her more distant, but still gentle toward people she trusts."
            />
            <button
              className="button"
              disabled={!!busy || !instruction.trim() || !!dirty}
              onClick={() =>
                action("Preparing suggested changes", async () => {
                  setProposal(
                    await api(`${base}/refine`, {
                      instruction,
                      expected_version: character.profile_version,
                    }),
                  );
                })
              }
            >
              ✧ Preview AI changes
            </button>
            {proposal && (
              <div className="proposal">
                <h3>Change preview</h3>
                <p>{proposal.explanation}</p>
                {proposal.changes.map((change) => (
                  <div className="diff" key={change.path}>
                    <strong>{labels[change.path] || change.path}</strong>
                    <div>
                      <del>{display(change.before)}</del>
                      <span>→</span>
                      <ins>{display(change.after)}</ins>
                    </div>
                  </div>
                ))}
                <div className="actions">
                  <button
                    className="button primary"
                    disabled={!!busy}
                    onClick={() =>
                      action("Applying changes", async () => {
                        update(
                          await api(`${base}/refine/confirm`, {
                            proposal_id: proposal.proposal_id,
                          }),
                        );
                        setVersions(await api(`${base}/versions`));
                        setInstruction("");
                        setNotice(
                          "Changes accepted. Your character identity and conversations are preserved.",
                        );
                      })
                    }
                  >
                    Accept changes
                  </button>
                  <button
                    className="button"
                    disabled={!!busy}
                    onClick={() => setProposal(null)}
                  >
                    Discard suggestion
                  </button>
                </div>
              </div>
            )}
          </section>
          <section className="panel">
            <h2>Profile versions</h2>
            <p className="muted">
              Restoring creates a new version and preserves your history.
            </p>
            <div className="version-list">
              {versions.map((v) => (
                <div key={v.version}>
                  <div>
                    <strong>
                      v{v.version} · {v.change_summary}
                    </strong>
                    <small className="muted">
                      {new Date(v.created_at).toLocaleString("en-US")}
                    </small>
                  </div>
                  {v.version === character.profile_version ? (
                    <span className="saved">Current version</span>
                  ) : (
                    <button
                      className="button"
                      disabled={!!busy || !!dirty}
                      onClick={() => {
                        if (
                          confirm(
                            `Restore profile v${v.version}? Conversations and portraits will stay unchanged.`,
                          )
                        )
                          void action("Restoring profile", async () => {
                            update(
                              await api(`${base}/restore`, {
                                version: v.version,
                                expected_version: character.profile_version,
                              }),
                            );
                            setVersions(await api(`${base}/versions`));
                            setNotice("Profile restored.");
                          });
                      }}
                    >
                      Restore
                    </button>
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
