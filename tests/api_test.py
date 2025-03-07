



import telnetlib 
  
# Connect to the Telnet server 
tn = telnetlib.Telnet("localhost", 7505) 
  
# Send a command to the server 
tn.write(b"status\n") 
  
# Read the output from the server 
output = tn.read_until(b"END")
  
# Print the output 
print(output.decode()) 
tn.close() 