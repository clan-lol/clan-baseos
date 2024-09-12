def get_instance_name(machine_name: str) -> str:
    return f"{machine_name}-single-disk"


# @API.register
# def set_single_disk_uuid(
#     base_path: str,
#     machine_name: str,
#     disk_uuid: str,
# ) -> None:
#     """
#     Set the disk UUID of single disk machine
#     """
#     inventory = load_inventory_json(base_path)

#     instance_name = get_instance_name(machine_name)

#     single_disk_config: ServiceSingleDisk = ServiceSingleDisk(
#         meta=ServiceMeta(name=instance_name),
#         roles=ServiceSingleDiskRole(
#             default=ServiceSingleDiskRoleDefault(
#                 config=SingleDiskConfig(device=f"/dev/disk/by-id/{disk_uuid}"),
#                 machines=[machine_name],
#             )
#         ),
#     )

#     inventory.services.single_disk[instance_name] = single_disk_config

#     save_inventory(
#         inventory,
#         base_path,
#         f"Set disk UUID: '{disk_uuid}' on machine: '{machine_name}'",
#     )
