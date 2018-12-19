# Shall we use a grouping structure around trace fragments?

A trace fragment is a set of events on a given EU that belong to the same trace.

Before sending the fragments it makes sense to buffer them for a short time to be able to compress the data before sending. A few seconds of delay is acceptable (say up to 10) but not beyond that as then buffering would cause noticeable delay.

A grouping structure makes sense if the data collected during the buffering period contains repetitive strings that can be factored out into a string registry so that we achieve some compression.

The stream of fragments is sharded by the trace ID. This reduces the volume of data that can be buffered in a given time window.

The number of trace fragments can go up to a few thousands per second, driven by vertical scaling of the power of a single computer. The number of partitions can be on the order of hundreds or thousands in a medium to large system, driven by the horizontal scale (number of computers).

The grouping structure seems to make sense even in a big system, but we need a way to control the buffering time.

A consequence is that the reporter needs to be aware of the number of partitions as it needs to maintain a registry per partition. Re-partittioning (shuffling) would become trouble-some as the registries would need to be split & merged. Using the same registry over all partition would alleviate this problem.

To avoid having to re-read the whole stream, the registry would neeed to be re-sent in the stream at times.

We also would need to take care of aging out the rarely used strings from the registry or register only the frequent ones (may have to rely on the user's mercy for this).

Or rely on a standard compression library (which again would reqire big buffers).
