# @API.register
# def set_admin_service(
#     base_url: str,
#     allowed_keys: dict[str, str],
#     instance_name: str = "admin",
#     extra_machines: list[str] | None = None,
# ) -> None:
#     """
#     Set the admin service of a clan
#     Every machine is by default part of the admin service via the 'all' tag
#     """
#     if extra_machines is None:
#         extra_machines = []
#     inventory = load_inventory_eval(base_url)

#     if not allowed_keys:
#         msg = "At least one key must be provided to ensure access"
#         raise ClanError(msg)

#     instance = ServiceAdmin(
#         meta=ServiceMeta(name=instance_name),
#         roles=ServiceAdminRole(
#             default=ServiceAdminRoleDefault(
#                 machines=extra_machines,
#                 tags=["all"],
#             )
#         ),
#         config=AdminConfig(allowedKeys=allowed_keys),
#     )

#     inventory.services.admin[instance_name] = instance

#     save_inventory(
#         inventory,
#         base_url,
#         f"Set admin service: '{instance_name}'",
#     )
