{ zerotierone, lib }:
# halalify zerotierone
zerotierone.overrideAttrs (_old: {
  meta = _old.meta // {
    license = lib.licenses.apsl20;
  };
})
