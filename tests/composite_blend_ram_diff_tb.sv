`timescale 1ns/1ps
module composite_blend_ram_diff_tb;
  reg clk=0;
  reg [2:0] mode=0;
  reg hblank_in=1,vblank_in=1,hsync_in=0,vsync_in=0,dotclk_in=0,interlace_in=0;
  reg [23:0] rgb_in=0;
  wire [23:0] rgb_original,rgb_ram;
  wire hb_original,vb_original,hs_original,vs_original,dot_original;
  wire hb_ram,vb_ram,hs_ram,vs_ram,dot_ram;
  integer checks=0;
  integer m,line,x,width,r,g,b;

  composite_blend_original original_dut(
    .clk(clk),.mode(mode),.hblank_in(hblank_in),.vblank_in(vblank_in),
    .hsync_in(hsync_in),.vsync_in(vsync_in),.dotclk_in(dotclk_in),
    .interlace_in(interlace_in),.rgb_in(rgb_in),.rgb_out(rgb_original),
    .hblank_out(hb_original),.vblank_out(vb_original),.hsync_out(hs_original),
    .vsync_out(vs_original),.dotclk_out(dot_original));
  composite_blend_ram ram_dut(
    .clk(clk),.mode(mode),.hblank_in(hblank_in),.vblank_in(vblank_in),
    .hsync_in(hsync_in),.vsync_in(vsync_in),.dotclk_in(dotclk_in),
    .interlace_in(interlace_in),.rgb_in(rgb_in),.rgb_out(rgb_ram),
    .hblank_out(hb_ram),.vblank_out(vb_ram),.hsync_out(hs_ram),
    .vsync_out(vs_ram),.dotclk_out(dot_ram));

  always #5 clk=~clk;

  task automatic tick;
    begin
      @(posedge clk); #1;
      if (rgb_original !== rgb_ram || hb_original !== hb_ram || vb_original !== vb_ram ||
          hs_original !== hs_ram || vs_original !== vs_ram || dot_original !== dot_ram)
        $fatal(1,"RAM inference changed output at check=%0d mode=%0d hb=%b rgb=%06h/%06h",
               checks,mode,hblank_in,rgb_original,rgb_ram);
      checks=checks+1;
    end
  endtask

  task automatic send(input [23:0] color,input bit hb,vb);
    begin
      @(negedge clk);
      rgb_in=color; hblank_in=hb; vblank_in=vb;
      hsync_in=checks[0]; dotclk_in=checks[0]; vsync_in=(checks==2);
      tick();
    end
  endtask

  initial begin
    tick();
    send(24'h000000,1,1);
    send(24'h000000,1,1);
    send(24'h000000,1,0);
    for (m=0;m<=6;m=m+1) begin
      mode=m[2:0];
      for(line=0;line<3;line=line+1) begin
        width=(line==0)?1:(line==1)?512:513;
        // Frame edges coincide with mode changes to exercise history resets.
        if (line==0 && m>0) begin
          send(24'h000000,1,1);
          send(24'h000000,1,0);
        end
        send(24'h000000,1,0);
        for(x=0;x<width;x=x+1) begin
          r=(x*73+line*41+m*17)&255;
          g=(x*29+line*89+m*53)&255;
          b=(x*137+line*11+m*97)&255;
          send({r[7:0],g[7:0],b[7:0]},0,0);
        end
        send(24'hffffff,1,0);
        send(24'h000000,1,0);
      end
    end
    send(24'h000000,1,1);
    send(24'h000000,1,1);
    $display("PASS: original/RAM-fixed outputs identical for %0d cycles",checks);
    $finish;
  end
endmodule
