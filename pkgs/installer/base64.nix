{ lib, ... }:
{
  toBase64 =
    text:
    let
      inherit (lib)
        sublist
        mod
        stringToCharacters
        concatMapStrings
        ;
      inherit (lib.strings) charToInt;
      inherit (builtins)
        substring
        foldl'
        genList
        elemAt
        length
        concatStringsSep
        stringLength
        ;
      lookup = stringToCharacters "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
      sliceN =
        size: list: n:
        sublist (n * size) size list;
      pows = [
        (64 * 64 * 64)
        (64 * 64)
        64
        1
      ];
      intSextets = i: map (j: mod (i / j) 64) pows;
      compose =
        f: g: x:
        f (g x);
      intToChar = elemAt lookup;
      convertTripletInt = sliceInt: concatMapStrings intToChar (intSextets sliceInt);
      sliceToInt = foldl' (acc: val: acc * 256 + val) 0;
      convertTriplet = compose convertTripletInt sliceToInt;
      join = concatStringsSep "";
      convertLastSlice =
        slice:
        let
          len = length slice;
        in
        if len == 1 then
          (substring 0 2 (convertTripletInt ((sliceToInt slice) * 256 * 256))) + "=="
        else if len == 2 then
          (substring 0 3 (convertTripletInt ((sliceToInt slice) * 256))) + "="
        else
          "";
      len = stringLength text;
      nFullSlices = len / 3;
      bytes = map charToInt (stringToCharacters text);
      tripletAt = sliceN 3 bytes;
      head = genList (compose convertTriplet tripletAt) nFullSlices;
      tail = convertLastSlice (tripletAt nFullSlices);
    in
    join (head ++ [ tail ]);
}
