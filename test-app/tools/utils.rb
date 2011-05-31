def get_uid_bytes file
  File.open(file) do |input|
    input.seek(0x08)
    lst = []
    4.times do
      lst << input.getc
    end
    lst
  end
end

def lookup_uid file
  b = get_uid_bytes(file)
  s = ("%c%c%c%c" % b.reverse)
  (s.unpack("N"))
end

def lookup_uid_s file
  uid = lookup_uid file
  "0x%08x" % uid
end
