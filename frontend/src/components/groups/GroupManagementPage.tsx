"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Archive,
  ArrowLeft,
  CheckCircle2,
  FolderKanban,
  Plus,
  RotateCcw,
  Trash2,
  UserPlus,
  Users
} from "lucide-react";

import {
  addGroupMember,
  archiveGroup,
  createGroup,
  createUser,
  deleteUser,
  listGroupMembers,
  listGroups,
  listUsers,
  removeGroupMember,
  restoreGroup,
  type GroupRecord,
  type MembershipRecord,
  type UserRecord
} from "@/lib/api";

const ROLES: MembershipRecord["role"][] = ["owner", "admin", "member", "viewer"];

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

function Badge({ children, tone = "neutral" }: { children: string; tone?: "neutral" | "good" | "warn" }) {
  const className =
    tone === "good"
      ? "bg-[rgba(15,139,141,0.12)] text-ocean"
      : tone === "warn"
        ? "bg-[rgba(212,106,74,0.12)] text-[var(--color-ember)]"
        : "bg-white/60 text-[var(--color-ink-soft)]";
  return <span className={`rounded-full px-3 py-1 text-xs ${className}`}>{children}</span>;
}

export function GroupManagementPage() {
  const [groups, setGroups] = useState<GroupRecord[]>([]);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [members, setMembers] = useState<MembershipRecord[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [includeDisabled, setIncludeDisabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [userForm, setUserForm] = useState({ id: "", displayName: "" });
  const [groupForm, setGroupForm] = useState({
    id: "",
    name: "",
    createdBy: "",
    description: "",
    defaultAgentId: "default"
  });
  const [memberForm, setMemberForm] = useState<{
    userId: string;
    role: MembershipRecord["role"];
  }>({ userId: "", role: "member" });

  const selectedGroup = useMemo(
    () => groups.find((group) => group.id === selectedGroupId) ?? groups[0] ?? null,
    [groups, selectedGroupId]
  );

  async function refreshGroups(nextIncludeArchived = includeArchived) {
    const nextGroups = await listGroups(nextIncludeArchived);
    setGroups(nextGroups);
    setSelectedGroupId((current) => {
      if (current && nextGroups.some((group) => group.id === current)) {
        return current;
      }
      return nextGroups[0]?.id ?? null;
    });
  }

  async function refreshUsers(nextIncludeDisabled = includeDisabled) {
    const nextUsers = await listUsers(nextIncludeDisabled);
    setUsers(nextUsers);
  }

  async function refreshMembers(groupId: string | null = selectedGroup?.id ?? null) {
    if (!groupId) {
      setMembers([]);
      return;
    }
    setMembers(await listGroupMembers(groupId));
  }

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const [nextGroups, nextUsers] = await Promise.all([
        listGroups(includeArchived),
        listUsers(includeDisabled)
      ]);
      setGroups(nextGroups);
      setUsers(nextUsers);
      const nextSelected = selectedGroupId && nextGroups.some((group) => group.id === selectedGroupId)
        ? selectedGroupId
        : nextGroups[0]?.id ?? null;
      setSelectedGroupId(nextSelected);
      if (nextSelected) {
        setMembers(await listGroupMembers(nextSelected));
      } else {
        setMembers([]);
      }
    } catch (nextError) {
      setError(getErrorMessage(nextError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void refreshMembers(selectedGroup?.id ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedGroup?.id]);

  async function runAction(action: () => Promise<void>, successMessage: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(successMessage);
    } catch (nextError) {
      setError(getErrorMessage(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function submitUser() {
    if (!userForm.id.trim()) {
      setError("User id is required");
      return;
    }
    await runAction(async () => {
      await createUser({
        id: userForm.id.trim(),
        display_name: userForm.displayName.trim() || undefined
      });
      setUserForm({ id: "", displayName: "" });
      await refreshUsers();
    }, "User created");
  }

  async function submitGroup() {
    if (!groupForm.id.trim() || !groupForm.name.trim() || !groupForm.createdBy.trim()) {
      setError("Group id, name and creator are required");
      return;
    }
    await runAction(async () => {
      const created = await createGroup({
        id: groupForm.id.trim(),
        name: groupForm.name.trim(),
        created_by: groupForm.createdBy.trim(),
        description: groupForm.description.trim(),
        default_agent_id: groupForm.defaultAgentId.trim() || "default"
      });
      setGroupForm({
        id: "",
        name: "",
        createdBy: "",
        description: "",
        defaultAgentId: "default"
      });
      await refreshGroups();
      setSelectedGroupId(created.id);
      await refreshMembers(created.id);
    }, "Group created");
  }

  async function submitMember() {
    if (!selectedGroup || !memberForm.userId.trim()) {
      setError("Select a group and user first");
      return;
    }
    await runAction(async () => {
      await addGroupMember(selectedGroup.id, {
        user_id: memberForm.userId.trim(),
        role: memberForm.role
      });
      setMemberForm({ userId: "", role: "member" });
      await refreshMembers(selectedGroup.id);
    }, "Member added");
  }

  async function toggleArchive(group: GroupRecord) {
    await runAction(async () => {
      if (group.status === "archived") {
        await restoreGroup(group.id);
      } else {
        await archiveGroup(group.id);
      }
      await refreshGroups();
    }, group.status === "archived" ? "Group restored" : "Group archived");
  }

  async function softDeleteUser(user: UserRecord) {
    await runAction(async () => {
      await deleteUser(user.id);
      await refreshUsers();
    }, "User disabled");
  }

  async function softRemoveMember(member: MembershipRecord) {
    if (!selectedGroup) {
      return;
    }
    await runAction(async () => {
      await removeGroupMember(selectedGroup.id, member.user_id);
      await refreshMembers(selectedGroup.id);
    }, "Member removed");
  }

  return (
    <main className="min-h-screen p-4 md:p-6">
      <div className="mx-auto flex max-w-[1800px] flex-col gap-4">
        <header className="panel flex flex-wrap items-center justify-between gap-4 rounded-[24px] px-5 py-4">
          <div className="flex items-center gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[rgba(15,139,141,0.14)] text-ocean">
              <FolderKanban size={20} />
            </div>
            <div>
              <p className="text-xs uppercase text-[var(--color-ink-soft)]">group console</p>
              <h1 className="text-xl font-semibold">组与用户管理</h1>
            </div>
          </div>
          <Link
            className="flex items-center gap-2 rounded-full border border-[var(--color-line)] bg-white/60 px-4 py-2 text-sm"
            href="/"
          >
            <ArrowLeft size={16} />
            返回聊天
          </Link>
        </header>

        {(error || notice) && (
          <div
            className={`rounded-[18px] border px-4 py-3 text-sm ${
              error
                ? "border-[rgba(212,106,74,0.28)] bg-[rgba(212,106,74,0.12)] text-[var(--color-ember)]"
                : "border-[rgba(15,139,141,0.22)] bg-[rgba(15,139,141,0.12)] text-ocean"
            }`}
          >
            {error ?? notice}
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)_420px]">
          <section className="panel min-h-[calc(100vh-150px)] rounded-[24px] p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-xs uppercase text-[var(--color-ink-soft)]">groups</p>
                <h2 className="text-lg font-semibold">知识库组</h2>
              </div>
              <label className="flex items-center gap-2 text-xs text-[var(--color-ink-soft)]">
                <input
                  checked={includeArchived}
                  onChange={(event) => {
                    setIncludeArchived(event.target.checked);
                    void refreshGroups(event.target.checked);
                  }}
                  type="checkbox"
                />
                含归档
              </label>
            </div>

            <div className="mb-4 space-y-2">
              <input
                className="w-full rounded-xl border border-[var(--color-line)] bg-white/65 px-3 py-2 text-sm"
                onChange={(event) => setGroupForm((prev) => ({ ...prev, id: event.target.value }))}
                placeholder="group_id"
                value={groupForm.id}
              />
              <input
                className="w-full rounded-xl border border-[var(--color-line)] bg-white/65 px-3 py-2 text-sm"
                onChange={(event) => setGroupForm((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="组名称"
                value={groupForm.name}
              />
              <input
                className="w-full rounded-xl border border-[var(--color-line)] bg-white/65 px-3 py-2 text-sm"
                onChange={(event) =>
                  setGroupForm((prev) => ({ ...prev, createdBy: event.target.value }))
                }
                placeholder="created_by"
                value={groupForm.createdBy}
              />
              <input
                className="w-full rounded-xl border border-[var(--color-line)] bg-white/65 px-3 py-2 text-sm"
                onChange={(event) =>
                  setGroupForm((prev) => ({ ...prev, defaultAgentId: event.target.value }))
                }
                placeholder="default_agent_id"
                value={groupForm.defaultAgentId}
              />
              <textarea
                className="min-h-20 w-full resize-none rounded-xl border border-[var(--color-line)] bg-white/65 px-3 py-2 text-sm"
                onChange={(event) =>
                  setGroupForm((prev) => ({ ...prev, description: event.target.value }))
                }
                placeholder="描述"
                value={groupForm.description}
              />
              <button
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-ocean px-3 py-2 text-sm text-white disabled:opacity-50"
                disabled={busy}
                onClick={() => void submitGroup()}
                type="button"
              >
                <Plus size={16} />
                创建组
              </button>
            </div>

            <div className="space-y-2">
              {loading ? (
                <p className="text-sm text-[var(--color-ink-soft)]">加载中...</p>
              ) : groups.length ? (
                groups.map((group) => (
                  <button
                    className={`w-full rounded-[16px] border px-3 py-3 text-left transition ${
                      group.id === selectedGroup?.id
                        ? "border-transparent bg-[rgba(15,139,141,0.15)]"
                        : "border-[var(--color-line)] bg-white/50"
                    }`}
                    key={group.id}
                    onClick={() => setSelectedGroupId(group.id)}
                    type="button"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{group.name}</p>
                        <p className="mt-1 text-xs text-[var(--color-ink-soft)]">{group.id}</p>
                      </div>
                      <Badge tone={group.status === "active" ? "good" : "warn"}>
                        {group.status}
                      </Badge>
                    </div>
                  </button>
                ))
              ) : (
                <p className="text-sm text-[var(--color-ink-soft)]">暂无组</p>
              )}
            </div>
          </section>

          <section className="panel min-h-[calc(100vh-150px)] rounded-[24px] p-5">
            {selectedGroup ? (
              <div className="flex h-full flex-col gap-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <Badge tone={selectedGroup.status === "active" ? "good" : "warn"}>
                        {selectedGroup.status}
                      </Badge>
                      <Badge>{selectedGroup.default_agent_id}</Badge>
                    </div>
                    <h2 className="text-2xl font-semibold">{selectedGroup.name}</h2>
                    <p className="mt-1 text-sm text-[var(--color-ink-soft)]">
                      {selectedGroup.description || "暂无描述"}
                    </p>
                  </div>
                  <button
                    className="flex items-center gap-2 rounded-xl border border-[var(--color-line)] bg-white/60 px-4 py-2 text-sm"
                    disabled={busy}
                    onClick={() => void toggleArchive(selectedGroup)}
                    type="button"
                  >
                    {selectedGroup.status === "archived" ? <RotateCcw size={16} /> : <Archive size={16} />}
                    {selectedGroup.status === "archived" ? "恢复" : "归档"}
                  </button>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-[16px] border border-[var(--color-line)] bg-white/50 p-4">
                    <p className="text-xs uppercase text-[var(--color-ink-soft)]">group id</p>
                    <p className="mt-2 font-medium">{selectedGroup.id}</p>
                  </div>
                  <div className="rounded-[16px] border border-[var(--color-line)] bg-white/50 p-4">
                    <p className="text-xs uppercase text-[var(--color-ink-soft)]">created by</p>
                    <p className="mt-2 font-medium">{selectedGroup.created_by}</p>
                  </div>
                  <div className="rounded-[16px] border border-[var(--color-line)] bg-white/50 p-4">
                    <p className="text-xs uppercase text-[var(--color-ink-soft)]">members</p>
                    <p className="mt-2 font-medium">{members.length}</p>
                  </div>
                </div>

                <div>
                  <h3 className="mb-3 flex items-center gap-2 font-semibold">
                    <CheckCircle2 size={18} />
                    知识库初始化路径
                  </h3>
                  <div className="grid gap-2 text-sm">
                    {["root", "documents", "uploads"].map((key) => (
                      <div
                        className="rounded-[14px] border border-[var(--color-line)] bg-white/50 px-3 py-2 mono"
                        key={key}
                      >
                        <span className="mr-3 text-[var(--color-ink-soft)]">{key}</span>
                        {selectedGroup.knowledge?.[key as keyof GroupRecord["knowledge"]] ?? "-"}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="min-h-0 flex-1">
                  <h3 className="mb-3 font-semibold">Memory policy</h3>
                  <pre className="max-h-[360px] overflow-auto rounded-[16px] border border-[var(--color-line)] bg-[rgba(13,37,48,0.9)] p-4 text-xs text-white">
                    {formatJson(selectedGroup.memory_policy)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-[var(--color-ink-soft)]">
                选择或创建一个组
              </div>
            )}
          </section>

          <section className="panel min-h-[calc(100vh-150px)] rounded-[24px] p-4">
            <div className="mb-5">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-[var(--color-ink-soft)]">users</p>
                  <h2 className="text-lg font-semibold">用户</h2>
                </div>
                <label className="flex items-center gap-2 text-xs text-[var(--color-ink-soft)]">
                  <input
                    checked={includeDisabled}
                    onChange={(event) => {
                      setIncludeDisabled(event.target.checked);
                      void refreshUsers(event.target.checked);
                    }}
                    type="checkbox"
                  />
                  含禁用
                </label>
              </div>
              <div className="grid grid-cols-[1fr_1fr_auto] gap-2">
                <input
                  className="min-w-0 rounded-xl border border-[var(--color-line)] bg-white/65 px-3 py-2 text-sm"
                  onChange={(event) => setUserForm((prev) => ({ ...prev, id: event.target.value }))}
                  placeholder="user_id"
                  value={userForm.id}
                />
                <input
                  className="min-w-0 rounded-xl border border-[var(--color-line)] bg-white/65 px-3 py-2 text-sm"
                  onChange={(event) =>
                    setUserForm((prev) => ({ ...prev, displayName: event.target.value }))
                  }
                  placeholder="名称"
                  value={userForm.displayName}
                />
                <button
                  className="flex h-10 w-10 items-center justify-center rounded-xl bg-ocean text-white disabled:opacity-50"
                  disabled={busy}
                  onClick={() => void submitUser()}
                  type="button"
                >
                  <UserPlus size={16} />
                </button>
              </div>
              <div className="mt-3 max-h-52 space-y-2 overflow-auto pr-1">
                {users.map((user) => (
                  <div
                    className="flex items-center justify-between gap-3 rounded-[14px] border border-[var(--color-line)] bg-white/50 px-3 py-2"
                    key={user.id}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{user.display_name}</p>
                      <p className="truncate text-xs text-[var(--color-ink-soft)]">{user.id}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={user.status === "active" ? "good" : "warn"}>
                        {user.status}
                      </Badge>
                      {user.status === "active" && (
                        <button
                          className="text-[var(--color-ember)]"
                          disabled={busy}
                          onClick={() => void softDeleteUser(user)}
                          type="button"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t border-[var(--color-line)] pt-5">
              <div className="mb-3 flex items-center gap-2">
                <Users size={18} />
                <h2 className="text-lg font-semibold">成员</h2>
              </div>
              <div className="grid grid-cols-[1fr_112px_auto] gap-2">
                <input
                  className="min-w-0 rounded-xl border border-[var(--color-line)] bg-white/65 px-3 py-2 text-sm"
                  onChange={(event) =>
                    setMemberForm((prev) => ({ ...prev, userId: event.target.value }))
                  }
                  placeholder="user_id"
                  value={memberForm.userId}
                />
                <select
                  className="rounded-xl border border-[var(--color-line)] bg-white/65 px-2 py-2 text-sm"
                  onChange={(event) =>
                    setMemberForm((prev) => ({
                      ...prev,
                      role: event.target.value as MembershipRecord["role"]
                    }))
                  }
                  value={memberForm.role}
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
                <button
                  className="flex h-10 w-10 items-center justify-center rounded-xl bg-ocean text-white disabled:opacity-50"
                  disabled={busy || !selectedGroup}
                  onClick={() => void submitMember()}
                  type="button"
                >
                  <Plus size={16} />
                </button>
              </div>
              <div className="mt-3 space-y-2">
                {members.map((member) => (
                  <div
                    className="flex items-center justify-between gap-3 rounded-[14px] border border-[var(--color-line)] bg-white/50 px-3 py-2"
                    key={`${member.group_id}:${member.user_id}`}
                  >
                    <div>
                      <p className="text-sm font-medium">{member.user_id}</p>
                      <p className="text-xs text-[var(--color-ink-soft)]">{member.role}</p>
                    </div>
                    <button
                      className="text-[var(--color-ember)]"
                      disabled={busy}
                      onClick={() => void softRemoveMember(member)}
                      type="button"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
                {!members.length && (
                  <p className="rounded-[14px] border border-[var(--color-line)] bg-white/45 px-3 py-3 text-sm text-[var(--color-ink-soft)]">
                    暂无成员
                  </p>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
