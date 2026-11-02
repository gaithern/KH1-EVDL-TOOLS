local MODULE_NAME = "KINGDOM HEARTS FINAL MIX.exe"
local GHIDRA_IMAGE_BASE = 0x140000000
local ENTITY_POOL = 0x142D372A0
local HANDLE_BUCKETS = 0x142EE3980
local ACTOR_SIZE = 0x4B0
local ACTOR_COUNT = 128
local BONE_RECORD_SIZE = 0x40
local FLOATS_PER_BONE = 16

local function steam_address(ghidra_address)
  return getAddress(MODULE_NAME) + (ghidra_address - GHIDRA_IMAGE_BASE)
end

local function resolve_handle(handle)
  if handle == nil or handle == 0 then
    return nil
  end
  local bucket = (handle & 0x7FFFFFFF) >> 25
  local base = readQword(steam_address(HANDLE_BUCKETS) + bucket * 8)
  return base | (handle & 0x1FFFFFF)
end

local function actor_address(index)
  return steam_address(ENTITY_POOL) + index * ACTOR_SIZE
end

local function actor_is_alive(actor)
  local flags = readInteger(actor + 0x374)
  return (flags & 1) == 1 and (flags & 2) == 0
end

local function actor_object_id(actor)
  local object_entry = resolve_handle(readInteger(actor + 0x130))
  if object_entry == nil then
    return -1
  end
  return readSmallInteger(object_entry + 0x4C)
end

function list_actors()
  for index = 0, ACTOR_COUNT - 1 do
    local actor = actor_address(index)
    if actor_is_alive(actor) then
      print(string.format("actor %d  object id %d (0x%X)  motion slot %d  time %.3f",
        index, actor_object_id(actor), actor_object_id(actor),
        readSmallInteger(actor + 0x168), readFloat(actor + 0x16C)))
    end
  end
end

local function read_bone_floats(array_handle, bone_count)
  local array = resolve_handle(array_handle)
  local rows = {}
  for bone = 0, bone_count - 1 do
    local values = {}
    for slot = 0, FLOATS_PER_BONE - 1 do
      values[#values + 1] = string.format("%.6f", readFloat(array + bone * BONE_RECORD_SIZE + slot * 4))
    end
    rows[#rows + 1] = "[" .. table.concat(values, ",") .. "]"
  end
  return "[" .. table.concat(rows, ",") .. "]"
end

local function read_matrix(address)
  local values = {}
  for slot = 0, FLOATS_PER_BONE - 1 do
    values[#values + 1] = string.format("%.6f", readFloat(address + slot * 4))
  end
  return "[" .. table.concat(values, ",") .. "]"
end

function dump_pose(index, path)
  pause()
  local actor = actor_address(index)
  local instance = resolve_handle(readInteger(actor + 0x15C))
  local model_header = readQword(readQword(instance))
  local bone_count = readSmallInteger(model_header)
  local channels = read_bone_floats(readInteger(instance + 0x1B0), bone_count)
  local world = read_bone_floats(readInteger(instance + 0x1B4), bone_count)
  local local_to_parent = read_bone_floats(readInteger(instance + 0x1B8), bone_count)
  local file = io.open(path, "w")
  file:write(string.format('{"actor": %d, "object_id": %d, "motion_slot": %d, "motion_time": %.6f, "bone_count": %d,\n',
    index, actor_object_id(actor), readSmallInteger(actor + 0x168), readFloat(actor + 0x16C), bone_count))
  file:write(string.format('"instance_flags": %d, "instance_time": %.6f, "blend_timer": %.6f,\n',
    readInteger(instance + 0x14), readFloat(instance + 0x10), readFloat(actor + 0x170)))
  file:write('"instance_root_matrix": ' .. read_matrix(instance + 0x130) .. ',\n')
  file:write('"actor_matrix": ' .. read_matrix(actor + 0xD0) .. ',\n')
  file:write('"sampled_channels": ' .. channels .. ',\n')
  file:write('"world_matrices": ' .. world .. ',\n')
  file:write('"local_matrices": ' .. local_to_parent .. '}\n')
  file:close()
  unpause()
  print("wrote " .. path .. " (" .. bone_count .. " bones)")
end
