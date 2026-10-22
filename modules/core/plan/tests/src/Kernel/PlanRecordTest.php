<?php

declare(strict_types=1);

namespace Drupal\Tests\plan\Kernel;

use Drupal\KernelTests\KernelTestBase;
use Drupal\plan\Entity\Plan;
use Drupal\plan\Entity\PlanRecord;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests for plan_record entities.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class PlanRecordTest extends KernelTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'entity',
    'plan',
    'plan_test',
    'user',
    'state_machine',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();
    $this->installEntitySchema('plan');
    $this->installEntitySchema('plan_record');
    $this->installConfig(['plan_test']);
  }

  /**
   * Test plan_record entities.
   */
  public function testPlanRecord() {

    // Get storage for plan and plan_record entities.
    $plan_storage = \Drupal::entityTypeManager()->getStorage('plan');
    $plan_record_storage = \Drupal::entityTypeManager()->getStorage('plan_record');

    // Create a plan entity.
    $plan = Plan::create([
      'name' => 'Test plan',
      'type' => 'default',
    ]);
    $plan->save();

    // Confirm that the plan entity was created.
    $plans = $plan_storage->loadMultiple();
    $this->assertCount(1, $plans);

    // Create two plan_record entities that reference the plan.
    $plan_record1 = PlanRecord::create([
      'plan' => $plan,
      'type' => 'default',
    ]);
    $plan_record1->save();
    $plan_record2 = PlanRecord::create([
      'plan' => $plan,
      'type' => 'default',
    ]);
    $plan_record2->save();

    // Confirm that the plan_record entities were created.
    $plan_records = $plan_record_storage->loadMultiple();
    $this->assertCount(2, $plan_records);

    // Delete the plan.
    $plan->delete();

    // Confirm that the plan and plan_record entities were all deleted.
    $plans = $plan_storage->loadMultiple();
    $this->assertCount(0, $plans);
    $plan_records = $plan_record_storage->loadMultiple();
    $this->assertCount(0, $plan_records);
  }

}
