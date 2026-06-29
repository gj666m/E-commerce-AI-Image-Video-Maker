<template>
  <div class="admin-page">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建用户
      </el-button>
    </div>

    <!-- 用户列表 -->
    <el-table :data="users" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="150" />
      <el-table-column prop="display_name" label="真实姓名" width="150">
        <template #default="{ row }">
          <span v-if="row.display_name">{{ row.display_name }}</span>
          <span v-else class="empty-name">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
            {{ row.role === 'admin' ? '管理员' : '用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" />
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)" :disabled="row.username === 'admin'">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建用户弹窗 -->
    <el-dialog v-model="showCreateDialog" title="创建用户" width="400px">
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="newUsername" placeholder="2-20 字符" />
        </el-form-item>
        <el-form-item label="真实姓名">
          <el-input v-model="newDisplayName" placeholder="可选，便于运营跟进" maxlength="50" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="newPassword" type="password" show-password placeholder="至少 4 位" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="newRole">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户弹窗 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="400px">
      <el-form label-width="80px">
        <el-form-item label="用户">
          <el-input :model-value="editUser?.username" disabled />
        </el-form-item>
        <el-form-item label="真实姓名">
          <el-input v-model="editDisplayName" placeholder="可选，便于运营跟进" maxlength="50" clearable />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="editPassword" type="password" show-password placeholder="留空则不修改" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleEdit" :loading="editing">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getUsers, createUser, deleteUser, updateUser, getErrorMessage } from '../api'
import type { UserItem } from '../types'

const users = ref<UserItem[]>([])
const loading = ref(false)

// 创建
const showCreateDialog = ref(false)
const newUsername = ref('')
const newDisplayName = ref('')
const newPassword = ref('')
const newRole = ref('user')
const creating = ref(false)

// 编辑用户（真实姓名 / 密码）
const showEditDialog = ref(false)
const editUser = ref<UserItem | null>(null)
const editDisplayName = ref('')
const editPassword = ref('')
const editing = ref(false)

async function fetchUsers() {
  loading.value = true
  try {
    const data = await getUsers()
    users.value = data.users
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '获取用户列表失败'))
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!newUsername.value || !newPassword.value) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  creating.value = true
  try {
    await createUser(newUsername.value, newPassword.value, newRole.value, newDisplayName.value)
    ElMessage.success('用户创建成功')
    showCreateDialog.value = false
    newUsername.value = ''
    newDisplayName.value = ''
    newPassword.value = ''
    newRole.value = 'user'
    await fetchUsers()
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '创建失败'))
  } finally {
    creating.value = false
  }
}

async function handleDelete(user: UserItem) {
  try {
    await ElMessageBox.confirm(`确定删除用户 "${user.username}"？该用户的所有数据将被清除。`, '确认删除', { type: 'warning' })
    await deleteUser(user.id)
    ElMessage.success('已删除')
    await fetchUsers()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(getErrorMessage(e, '删除失败'))
    }
  }
}

function openEditDialog(user: UserItem) {
  editUser.value = user
  editDisplayName.value = user.display_name || ''
  editPassword.value = ''
  showEditDialog.value = true
}

async function handleEdit() {
  if (!editPassword.value && editDisplayName.value === (editUser.value?.display_name || '')) {
    ElMessage.warning('没有需要更新的字段')
    return
  }
  editing.value = true
  try {
    const payload: { password?: string; display_name?: string } = {}
    if (editPassword.value) payload.password = editPassword.value
    if (editDisplayName.value !== (editUser.value?.display_name || '')) {
      payload.display_name = editDisplayName.value
    }
    await updateUser(editUser.value!.id, payload)
    ElMessage.success('已保存')
    showEditDialog.value = false
    await fetchUsers()
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '保存失败'))
  } finally {
    editing.value = false
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.admin-page {
  max-width: 800px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
}

.empty-name {
  color: var(--el-text-color-placeholder);
}
</style>
