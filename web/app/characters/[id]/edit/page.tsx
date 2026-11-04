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
    title: "基本信息",
    subtitle: "故事从这里开始",
    fields: [
      ["name", "名字"],
      ["short_description", "一句话介绍"],
      ["backstory", "背景故事"],
    ],
  },
  {
    title: "外貌",
    subtitle: "想象 TA 的样子",
    fields: [
      ["appearance.age_description", "年龄描述"],
      ["appearance.hair", "头发"],
      ["appearance.eyes", "眼睛"],
      ["appearance.clothing", "服饰"],
      ["appearance.other_details", "其他特征"],
    ],
  },
  {
    title: "性格",
    subtitle: "让角色有自己的内在世界",
    fields: [
      ["personality.core_traits", "核心特质"],
      ["personality.values", "价值观"],
      ["personality.motivations", "动机"],
      ["personality.behavioral_patterns", "行为习惯"],
    ],
  },
  {
    title: "说话与相处",
    subtitle: "属于 TA 的表达方式",
    fields: [
      ["speech_style.tone", "语气"],
      ["speech_style.vocabulary", "用词风格"],
      ["speech_style.speaking_habits", "常用表达"],
      ["interaction_preferences.conversation_style", "对话方式"],
      ["interaction_preferences.relationship_context", "与你的关系"],
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
    ? value.join("、") || "（空）"
    : value || "（空）";
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
              重试
            </button>
          </div>
        ) : (
          <p role="status">正在打开角色工作室…</p>
        )}
      </main>
    );
  return (
    <main className="container editor-container">
      <Link
        className="back-link"
        href="/characters"
        onClick={(e) => {
          if (dirty && !confirm("还有未保存的修改，确定离开？"))
            e.preventDefault();
        }}
      >
        ← 我的角色
      </Link>
      <section className="page-intro compact">
        <div>
          <p className="eyebrow">CHARACTER STUDIO</p>
          <h1>塑造 {character.profile.name}</h1>
          <p className="muted">每一个细节，都让 TA 更接近你的想象。</p>
        </div>
        <Link
          className="button"
          href={`${base}/chat`}
          onClick={(e) => {
            if (dirty && !confirm("修改尚未保存。使用已保存的设定开始对话？"))
              e.preventDefault();
          }}
        >
          开始对话 ↗
        </Link>
      </section>
      <div className="status-bar" aria-live="polite">
        <span className={dirty ? "unsaved" : "saved"}>
          {dirty
            ? "● 有未保存的修改"
            : `✓ 已保存 · 设定 v${character.profile_version}`}
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
            <p className="muted">头像是可选的，先开始对话也很好。</p>
            <label htmlFor="visual-style">画面风格</label>
            <select
              id="visual-style"
              value={profile.visual_style}
              disabled={!!busy}
              onChange={(e) => setField("visual_style", e.target.value)}
            >
              {[
                ["Anime", "动漫"],
                ["Cartoon", "卡通"],
                ["Semi-realistic", "半写实"],
                ["Realistic", "写实"],
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
                action("正在生成头像，请稍候", async () => {
                  await api(`${base}/images/generate`, {
                    expected_image_id: character.current_image_id,
                  });
                  setImages(await api(`${base}/images`));
                  setNotice("新头像已生成，请在下方预览并选用。");
                })
              }
            >
              ✧ 生成头像
            </button>
            {dirty && (
              <small className="muted">
                请先保存设定，再生成头像或让 AI 修改。
              </small>
            )}
            {character.current_image_id && (
              <>
                <label htmlFor="image-edit">修改当前头像</label>
                <textarea
                  id="image-edit"
                  rows={3}
                  maxLength={2000}
                  value={imageInstruction}
                  disabled={!!busy}
                  onChange={(e) => setImageInstruction(e.target.value)}
                  placeholder="例如：头发改成深蓝色，保留其他细节"
                />
                <small className="muted">
                  AI 编辑可能改变其他细节。原图会保留，请预览后选用。
                </small>
                <button
                  className="button full"
                  disabled={!!busy || !imageInstruction.trim() || !!dirty}
                  onClick={() =>
                    action("正在修改头像，请稍候", async () => {
                      await api(`${base}/images/edit`, {
                        instruction: imageInstruction,
                        expected_image_id: character.current_image_id,
                      });
                      setImages(await api(`${base}/images`));
                      setNotice("修改完成，请对比并选用新版本。");
                    })
                  }
                >
                  修改头像
                </button>
              </>
            )}
          </section>
          {images.length > 0 && (
            <section className="panel">
              <h3>头像版本</h3>
              <p className="muted small">选用只改变头像，不会改动人物设定。</p>
              <div className="image-history">
                {images.map((image) => (
                  <div
                    key={image.id}
                    className={`image-version ${image.id === character.current_image_id ? "selected" : ""}`}
                  >
                    <img src={image.url} alt={`头像版本 ${image.version}`} />
                    <small>
                      v{image.version}
                      {image.parent_image_id ? " · 编辑" : " · 生成"}
                    </small>
                    {image.id === character.current_image_id ? (
                      <span className="saved">使用中</span>
                    ) : (
                      <>
                        <button
                          disabled={!!busy}
                          onClick={() =>
                            action("正在选用头像", async () => {
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
                              setNotice("头像已保存。");
                            })
                          }
                        >
                          选用此版
                        </button>
                        <button
                          className="text-button danger"
                          disabled={!!busy}
                          onClick={() =>
                            action("正在移除图片", async () => {
                              await api(
                                `${base}/images/${image.id}`,
                                undefined,
                                "DELETE",
                              );
                              setImages(await api(`${base}/images`));
                            })
                          }
                        >
                          丢弃
                        </button>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
          <section className="panel">
            <h3>最初的灵感</h3>
            <p className="original-description">
              {character.original_description}
            </p>
            <p className="muted small">
              请对照原始要求检查 AI
              建议。未指定的内容可能是创作补充，所有字段均可修改。
            </p>
          </section>
        </aside>
        <div className="profile-column">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void action("正在保存设定", async () => {
                const c = await api<Character>(
                  base,
                  { profile, expected_version: character.profile_version },
                  "PATCH",
                );
                update(c);
                setVersions(await api(`${base}/versions`));
                setNotice("修改已保存，后续对话会使用新的设定。");
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
                          <span className="field-hint"> · 每行一项</span>
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
                  ? "保存后，新设定会用于之后的对话。"
                  : "设定与对话分别保存，你可以随时回来。"}
              </p>
              <button
                className="button primary"
                disabled={!!busy || !dirty || !profile.name.trim()}
              >
                保存修改
              </button>
            </div>
          </form>
          <section className="panel refine-panel">
            <p className="eyebrow">SHAPE, DON’T RESTART</p>
            <h2>用一句话，调整 TA。</h2>
            <p className="muted">
              我们会先展示修改建议，由你决定是否采用。对话和头像会保留。
            </p>
            <label htmlFor="refinement">你希望怎样调整？</label>
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
              placeholder="让她更冷淡一点，但对信任的人仍然温柔。"
            />
            <button
              className="button"
              disabled={!!busy || !instruction.trim() || !!dirty}
              onClick={() =>
                action("正在构思修改建议", async () => {
                  setProposal(
                    await api(`${base}/refine`, {
                      instruction,
                      expected_version: character.profile_version,
                    }),
                  );
                })
              }
            >
              ✧ 预览 AI 修改
            </button>
            {proposal && (
              <div className="proposal">
                <h3>修改预览</h3>
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
                      action("正在应用修改", async () => {
                        update(
                          await api(`${base}/refine/confirm`, {
                            proposal_id: proposal.proposal_id,
                          }),
                        );
                        setVersions(await api(`${base}/versions`));
                        setInstruction("");
                        setNotice("已采用建议，角色身份和对话保持连续。");
                      })
                    }
                  >
                    采用这些修改
                  </button>
                  <button
                    className="button"
                    disabled={!!busy}
                    onClick={() => setProposal(null)}
                  >
                    放弃建议
                  </button>
                </div>
              </div>
            )}
          </section>
          <section className="panel">
            <h2>设定版本</h2>
            <p className="muted">恢复会另存为新版本，保留全部历史。</p>
            <div className="version-list">
              {versions.map((v) => (
                <div key={v.version}>
                  <div>
                    <strong>
                      v{v.version} · {v.change_summary}
                    </strong>
                    <small className="muted">
                      {new Date(v.created_at).toLocaleString("zh-CN")}
                    </small>
                  </div>
                  {v.version === character.profile_version ? (
                    <span className="saved">当前版本</span>
                  ) : (
                    <button
                      className="button"
                      disabled={!!busy || !!dirty}
                      onClick={() => {
                        if (
                          confirm(
                            `将设定恢复到 v${v.version}？对话和头像保持不变。`,
                          )
                        )
                          void action("正在恢复设定", async () => {
                            update(
                              await api(`${base}/restore`, {
                                version: v.version,
                                expected_version: character.profile_version,
                              }),
                            );
                            setVersions(await api(`${base}/versions`));
                            setNotice("设定已恢复。");
                          });
                      }}
                    >
                      恢复
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
