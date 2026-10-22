<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_entity\Functional;

use Drupal\Tests\farm_test\Functional\FarmBrowserTestBase;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Test expected farmOS entity revision behavior.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class FarmEntityRevisionsTest extends FarmBrowserTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'farm_entity',
    'farm_entity_test',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    // Create and login a user with access to entity revisions.
    $user = $this->createuser([
      'view any asset',
      'view any log',
      'view any plan',
      'view all asset revisions',
      'view all log revisions',
      'view all plan revisions',
    ]);
    $this->drupalLogin($user);
  }

  /**
   * Test expected farmOS entity revision behavior.
   */
  public function testFarmEntityRevisions() {
    $entity_types = [
      'asset',
      'log',
      'plan',
    ];
    foreach ($entity_types as $entity_type) {
      $storage = \Drupal::entityTypeManager()->getStorage($entity_type);

      // Create a test entity.
      /** @var \Drupal\Core\Entity\RevisionLogInterface $entity */
      $entity = $storage->create([
        'name' => $this->randomMachineName(),
        'type' => 'test',
      ]);
      $entity->setRevisionLogMessage('First revision log.');
      $entity->save();

      // Create a second revision and remember both revision IDs.
      $first_revision_id = $entity->getRevisionId();
      $entity->setNewRevision();
      $entity->setRevisionLogMessage('Second revision log.');
      $entity->save();
      $second_revision_id = $entity->getRevisionId();
      $this->assertNotEquals($first_revision_id, $second_revision_id);

      // Confirm that a /revisions tab is available.
      $this->drupalGet($entity_type . '/' . $entity->id() . '/revisions');
      $this->assertSession()->statusCodeEquals(200);

      // Confirm that both revisions are shown in the /revisions tab.
      $this->assertSession()->pageTextContains('First revision log');
      $this->assertSession()->pageTextContains('Second revision log');

      // Test that entity revisions cannot be reverted.
      $this->assertSession()->responseNotContains('Revert');
      $this->drupalGet($entity_type . '/' . $entity->id() . '/revisions/' . $first_revision_id . '/revert');
      $this->assertSession()->statusCodeEquals(404);
    }
  }

}
