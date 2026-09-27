// Example: Async FIFO - Test design for AstrixCore Verification AI
// This is a realistic RTL module that exercises all platform capabilities

module async_fifo #(
    parameter DATA_WIDTH = 32,
    parameter ADDR_WIDTH = 4,
    parameter DEPTH = (1 << ADDR_WIDTH)
)(
    // Write interface
    input  wire                  wr_clk,
    input  wire                  wr_rst_n,
    input  wire                  wr_en,
    input  wire [DATA_WIDTH-1:0] wr_data,
    output wire                  full,

    // Read interface
    input  wire                  rd_clk,
    input  wire                  rd_rst_n,
    input  wire                  rd_en,
    output wire [DATA_WIDTH-1:0] rd_data,
    output wire                  empty,

    // Status
    output wire [$clog2(DEPTH):0] fifo_count
);

    // Memory
    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // Write pointer (gray code)
    reg [ADDR_WIDTH:0] wr_ptr;
    reg [ADDR_WIDTH:0] wr_ptr_gray;
    reg [ADDR_WIDTH:0] wr_ptr_gray_sync1;
    reg [ADDR_WIDTH:0] wr_ptr_gray_sync2;

    // Read pointer (gray code)
    reg [ADDR_WIDTH:0] rd_ptr;
    reg [ADDR_WIDTH:0] rd_ptr_gray;
    reg [ADDR_WIDTH:0] rd_ptr_gray_sync1;
    reg [ADDR_WIDTH:0] rd_ptr_gray_sync2;

    // Binary to Gray conversion
    function [ADDR_WIDTH:0] bin2gray(input [ADDR_WIDTH:0] bin);
        bin2gray = bin ^ (bin >> 1);
    endfunction

    // Write logic
    always @(posedge wr_clk or negedge wr_rst_n) begin
        if (!wr_rst_n) begin
            wr_ptr <= 0;
            wr_ptr_gray <= 0;
        end else if (wr_en && !full) begin
            mem[wr_ptr[ADDR_WIDTH-1:0]] <= wr_data;
            wr_ptr <= wr_ptr + 1;
            wr_ptr_gray <= bin2gray(wr_ptr + 1);
        end
    end

    // Read logic
    always @(posedge rd_clk or negedge rd_rst_n) begin
        if (!rd_rst_n) begin
            rd_ptr <= 0;
            rd_ptr_gray <= 0;
        end else if (rd_en && !empty) begin
            rd_ptr <= rd_ptr + 1;
            rd_ptr_gray <= bin2gray(rd_ptr + 1);
        end
    end

    assign rd_data = mem[rd_ptr[ADDR_WIDTH-1:0]];

    // Synchronize write pointer to read clock domain
    always @(posedge rd_clk or negedge rd_rst_n) begin
        if (!rd_rst_n) begin
            wr_ptr_gray_sync1 <= 0;
            wr_ptr_gray_sync2 <= 0;
        end else begin
            wr_ptr_gray_sync1 <= wr_ptr_gray;
            wr_ptr_gray_sync2 <= wr_ptr_gray_sync1;
        end
    end

    // Synchronize read pointer to write clock domain
    always @(posedge wr_clk or negedge wr_rst_n) begin
        if (!wr_rst_n) begin
            rd_ptr_gray_sync1 <= 0;
            rd_ptr_gray_sync2 <= 0;
        end else begin
            rd_ptr_gray_sync1 <= rd_ptr_gray;
            rd_ptr_gray_sync2 <= rd_ptr_gray_sync1;
        end
    end

    // Full flag (write domain)
    assign full = (wr_ptr_gray == {~rd_ptr_gray_sync2[ADDR_WIDTH:ADDR_WIDTH-1],
                                     rd_ptr_gray_sync2[ADDR_WIDTH-2:0]});

    // Empty flag (read domain)
    assign empty = (rd_ptr_gray == wr_ptr_gray_sync2);

    // FIFO count (approximate, write domain)
    assign fifo_count = wr_ptr - rd_ptr;

    // Assertions
    property p_no_write_when_full;
        @(posedge wr_clk) disable iff (!wr_rst_n)
        full |-> !wr_en;
    endproperty
    a_no_write_when_full: assert property (p_no_write_when_full);

    property p_no_read_when_empty;
        @(posedge rd_clk) disable iff (!rd_rst_n)
        empty |-> !rd_en;
    endproperty
    a_no_read_when_empty: assert property (p_no_read_when_empty);

    property p_wr_ptr_increments;
        @(posedge wr_clk) disable iff (!wr_rst_n)
        (wr_en && !full) |=> (wr_ptr == $past(wr_ptr) + 1);
    endproperty
    a_wr_ptr_increments: assert property (p_wr_ptr_increments);

    property p_rd_ptr_increments;
        @(posedge rd_clk) disable iff (!rd_rst_n)
        (rd_en && !empty) |=> (rd_ptr == $past(rd_ptr) + 1);
    endproperty
    a_rd_ptr_increments: assert property (p_rd_ptr_increments);

endmodule


// Simple FSM Controller - Another test module
module traffic_light_controller (
    input  wire clk,
    input  wire rst_n,
    input  wire sensor,
    output reg  [1:0] light_ns,
    output reg  [1:0] light_ew
);

    // FSM States
    typedef enum logic [1:0] {
        GREEN_NS  = 2'b00,
        YELLOW_NS = 2'b01,
        GREEN_EW  = 2'b10,
        YELLOW_EW = 2'b11
    } state_t;

    state_t current_state, next_state;

    // State register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            current_state <= GREEN_NS;
        else
            current_state <= next_state;
    end

    // Next state logic
    always @(*) begin
        case (current_state)
            GREEN_NS:  next_state = sensor ? GREEN_NS : YELLOW_NS;
            YELLOW_NS: next_state = GREEN_EW;
            GREEN_EW:  next_state = sensor ? GREEN_EW : YELLOW_EW;
            YELLOW_EW: next_state = GREEN_NS;
            default:   next_state = GREEN_NS;
        endcase
    end

    // Output logic
    always @(*) begin
        case (current_state)
            GREEN_NS:  begin light_ns = 2'b10; light_ew = 2'b00; end
            YELLOW_NS: begin light_ns = 2'b01; light_ew = 2'b00; end
            GREEN_EW:  begin light_ns = 2'b00; light_ew = 2'b10; end
            YELLOW_EW: begin light_ns = 2'b00; light_ew = 2'b01; end
            default:   begin light_ns = 2'b00; light_ew = 2'b00; end
        endcase
    end

    // FSM assertions
    property p_legal_transitions;
        @(posedge clk) disable iff (!rst_n)
        ($changed(current_state)) |-> (
            (current_state == GREEN_NS && next_state == YELLOW_NS) ||
            (current_state == YELLOW_NS && next_state == GREEN_EW) ||
            (current_state == GREEN_EW && next_state == YELLOW_EW) ||
            (current_state == YELLOW_EW && next_state == GREEN_NS)
        );
    endproperty
    a_legal_transitions: assert property (p_legal_transitions);

    property p_valid_state;
        @(posedge clk) disable iff (!rst_n)
        current_state inside {GREEN_NS, YELLOW_NS, GREEN_EW, YELLOW_EW};
    endproperty
    a_valid_state: assert property (p_valid_state);

endmodule


// Pipelined Adder - Tests pipeline verification
module pipelined_adder #(
    parameter DATA_WIDTH = 32,
    parameter STAGES = 3
)(
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  valid_in,
    input  wire [DATA_WIDTH-1:0] a,
    input  wire [DATA_WIDTH-1:0] b,
    output reg  [DATA_WIDTH-1:0] result,
    output reg                   valid_out
);

    // Pipeline registers
    reg [DATA_WIDTH-1:0] pipe_a [0:STAGES-1];
    reg [DATA_WIDTH-1:0] pipe_b [0:STAGES-1];
    reg [DATA_WIDTH-1:0] pipe_sum [0:STAGES-1];
    reg valid_pipe [0:STAGES-1];

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < STAGES; i = i + 1) begin
                pipe_a[i] <= 0;
                pipe_b[i] <= 0;
                pipe_sum[i] <= 0;
                valid_pipe[i] <= 0;
            end
            result <= 0;
            valid_out <= 0;
        end else begin
            // Stage 1: Register inputs
            pipe_a[0] <= a;
            pipe_b[0] <= b;
            valid_pipe[0] <= valid_in;

            // Pipeline stages
            for (i = 1; i < STAGES; i = i + 1) begin
                pipe_a[i] <= pipe_a[i-1];
                pipe_b[i] <= pipe_b[i-1];
                pipe_sum[i] <= pipe_sum[i-1];
                valid_pipe[i] <= valid_pipe[i-1];
            end

            // Final stage: compute and output
            pipe_sum[STAGES-1] <= pipe_a[STAGES-1] + pipe_b[STAGES-1];
            result <= pipe_sum[STAGES-1];
            valid_out <= valid_pipe[STAGES-1];
        end
    end

endmodule
